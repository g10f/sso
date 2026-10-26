import json
import logging
from functools import wraps
from datetime import timedelta
from urllib.parse import urlparse, urlunparse, urlsplit, urlunsplit

from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from oauthlib import oauth2
from oauthlib.common import Request
from oauthlib.common import urlencode, urlencoded, quote
from oauthlib.oauth2.rfc6749.utils import scope_to_list

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponseRedirect, HttpResponse, QueryDict
from django.http.response import HttpResponseRedirectBase, Http404
from django.shortcuts import render, get_object_or_404, resolve_url
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri, force_str
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.cache import never_cache, cache_page, cache_control
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView
from sso.api.response import JsonHttpResponse, same_origin, add_cors_header
from sso.api.views.generic import PreflightMixin
from sso.auth.utils import is_recent_auth_time
from sso.auth.views import TWO_FACTOR_PARAM
from sso.middleware import revision_exempt
from sso.utils.http import get_request_param
from sso.utils.url import get_base_url
from .crypt import loads_jwt
from .keys import get_public_keys, get_certs, get_certs_jwks
from .models import Client, DeviceCode, DEVICE_CODE_GRANT_TYPE, check_redirect_uri, normalize_user_code
from .oidc_server import oidc_server, oidc_request_validator, device_authorization_endpoint

logger = logging.getLogger(__name__)


def _get_escaped_full_path(request):
    """
    Django considers "safe" some characters that aren't so for oauthlib. We have to search for
    them and properly escape.
    """
    uri = request.build_absolute_uri()
    parsed = list(urlparse(uri))
    unsafe = set(c for c in parsed[4]).difference(urlencoded)
    for c in unsafe:
        parsed[4] = parsed[4].replace(c, quote(c, safe=''))
    return urlunparse(parsed)


def extract_params(request):
    logger.debug('Extracting parameters from request.')
    uri = _get_escaped_full_path(request)
    http_method = request.method
    headers = request.headers
    body = urlencode(request.POST.items())
    return uri, http_method, body, headers


def pop_query_param(url, param_name):
    """
    get the query param with the param_name from the url and
    return a new url without that param_name and
    return the value of the param_name
    """
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    query_dict = QueryDict(query).copy()
    # get the last value
    value = query_dict.get(param_name, None)
    if value:
        del query_dict[param_name]
    query = query_dict.urlencode()
    return urlunsplit((scheme, netloc, path, query, fragment)), value


class HttpOAuth2ResponseRedirect(HttpResponseRedirect):
    """
    don't check the location, because this was already done in OAuth2RequestValidator::validate_redirect_uri
    and we have custom schemas for android and iOS apps
    """

    def __init__(self, redirect_to, *args, **kwargs):
        if redirect_to.startswith('urn:ietf:wg:oauth:2.0:oob'):
            redirect_to = redirect_to.replace('urn:ietf:wg:oauth:2.0:oob', reverse('oauth2:approval'), 1)

        super(HttpResponseRedirectBase, self).__init__(*args, **kwargs)
        self['Location'] = iri_to_uri(redirect_to)


@method_decorator(revision_exempt, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserInfoView(PreflightMixin, View):
    """
    OpenID Connect userinfo endpoint
    see https://openid.net/specs/openid-connect-core-1_0.html#UserInfo
    """
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        uri, http_method, body, headers = extract_params(request)
        try:
            headers, body, status = oidc_server.create_userinfo_response(uri, http_method, body, headers)
        except oauth2.OAuth2Error as e:
            headers, body, status = {**e.headers, 'Content-Type': 'application/json'}, e.json, e.status_code
        response = HttpResponse(content=body, status=status)
        for k, v in headers.items():
            response[k] = v
        # only bearer tokens and no cookies are accepted, so every origin is allowed
        add_cors_header(request.META.get('HTTP_ORIGIN'), None, response, public_cors=True)
        return response

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


@method_decorator(cache_page(60 * 60), name='dispatch')
@method_decorator(vary_on_headers('Origin', 'Accept-Language'), name='dispatch')
class OpenidConfigurationView(PreflightMixin, View):
    http_method_names = ['get', 'options']

    def get(self, request, *args, **kwargs):
        """
        http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
        """
        base_uri = get_base_url(request)  # 'http://10.0.2.2:8000'  # for android local client test
        if settings.SSO_LEGACY_USERINFO_ENDPOINT:
            # temporary, until all clients use the standard userinfo endpoint
            userinfo_endpoint = reverse('api:v2_users_me')
        else:
            userinfo_endpoint = reverse('oauth2:userinfo')
        configuration = {
            "issuer": base_uri,
            "authorization_endpoint": '%s%s' % (base_uri, reverse('oauth2:authorize')),
            "token_endpoint": '%s%s' % (base_uri, reverse('oauth2:token')),
            "userinfo_endpoint": '%s%s' % (base_uri, userinfo_endpoint),
            "revocation_endpoint": '%s%s' % (base_uri, reverse('oauth2:revoke')),
            "jwks_uri": '%s%s' % (base_uri, reverse('oauth2:jwks')),
            "scopes_supported":
                ['openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture'],
            "response_types_supported":
                ["code", "token", "id_token token", "id_token"],
            # if omitted, clients must assume ["authorization_code", "implicit"]
            "grant_types_supported":
                ["authorization_code", "implicit", "refresh_token", "client_credentials", "password"],
            "id_token_signing_alg_values_supported":
                ["RS256"],
            "token_endpoint_auth_methods_supported":
                ["client_secret_basic", "client_secret_post"],
            "token_endpoint_auth_signing_alg_values_supported":
                ["RS256"],
            "display_values_supported":
                ["page", "popup"],
            "subject_types_supported":
                ["public"],
            "end_session_endpoint": '%s%s' % (base_uri, reverse('auth:logout')),
            "introspection_endpoint": '%s%s' % (base_uri, reverse('oauth2:introspect')),
            "check_session_iframe": '%s%s' % (base_uri, reverse('oauth2:session')),
            # "certs_uri": '%s%s' % (base_uri, reverse('oauth2:certs')),
            "profile_uri": '%s%s' % (base_uri, reverse('accounts:profile')),
        }
        if settings.SSO_DEVICE_AUTHORIZATION_GRANT:
            configuration['device_authorization_endpoint'] = '%s%s' % (base_uri, reverse('oauth2:device_authorization'))
            configuration['grant_types_supported'].append(DEVICE_CODE_GRANT_TYPE)
        if settings.SSO_SERVICE_DOCUMENTATION:
            configuration['service_documentation'] = settings.SSO_SERVICE_DOCUMENTATION
        return JsonHttpResponse(configuration, request, allow_jsonp=True, public_cors=True)


class JwksView(PreflightMixin, View):
    http_method_names = ['get', 'options']

    def get(self, request, *args, **kwargs):
        """
        jwks_uri view (http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata)
        """
        certs = get_certs_jwks()

        rsa256 = RSAAlgorithm(RSAAlgorithm.SHA256)
        keys = []
        for pub_key in get_public_keys():
            key_obj = rsa256.prepare_key(pub_key.value)
            key = json.loads(RSAAlgorithm.to_jwk(key_obj))
            key["kid"] = pub_key.component.uuid.hex
            key["alg"] = pub_key.component.name
            key["use"] = "sig"
            if pub_key.component.uuid.hex in certs:
                key.update(certs[pub_key.component.uuid.hex])
            keys.append(key)
        data = {'keys': keys}
        return JsonHttpResponse(data, request, allow_jsonp=True, public_cors=True)


class CertsView(PreflightMixin, View):
    http_method_names = ['get', 'options']

    def get(self, request, *args, **kwargs):
        certs = {}
        for cert in get_certs():
            certs[cert.component.uuid.hex] = cert.value

        return JsonHttpResponse(certs, request, allow_jsonp=True, public_cors=True)


class SessionView(TemplateView):
    @method_decorator(cache_control(max_age=60 * 5))
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session_cookie_name'] = settings.SSO_OIDC_SESSION_COOKIE_NAME
        return context


def session_init(request):
    client_id = request.GET.get('client_id')
    origin = request.GET.get('origin')
    try:
        client = Client.objects.get(uuid=client_id)
    except (Client.DoesNotExist, ValidationError, ValueError):
        raise Http404()

    for redirect_uri in client.redirect_uris.split():
        if same_origin(redirect_uri, origin):
            return HttpResponse(status=204)
    raise Http404()


def redirect_to_login(request, redirect_field_name=REDIRECT_FIELD_NAME, two_factor=False):  # @ReservedAssignment
    """
    Redirects the user to the login page, passing the given 'next' page
    if there is a display parameter in the url we extract this parameter from the next url
    and pass it directly to the login url
    """
    resolved_login_url = force_str(resolve_url(settings.LOGIN_URL))
    full_path = request.get_full_path()
    redirect_url, display = pop_query_param(full_path, 'display')

    login_url_parts = list(urlparse(resolved_login_url))

    querystring = QueryDict(login_url_parts[4], mutable=True)
    if redirect_field_name:
        querystring[redirect_field_name] = redirect_url
        if display:
            querystring['display'] = display
    if two_factor:
        querystring[TWO_FACTOR_PARAM] = '1'

    login_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(login_url_parts))


def get_oidc_session_state(request):
    if request.session.session_key is None:
        data = ""
    else:
        data = request.session.session_key
    key_salt = 'get_oidc_session_state'
    return salted_hmac(key_salt, data, algorithm='sha256').hexdigest()


class TwoFactorRequiredError(oauth2.OAuth2Error):
    error = 'two_factor_required'
    description = 'The End User has no "two factor" device.'


def get_acr_claim(request):
    claims = json.loads(get_request_param(request, 'claims', '{}'))
    try:
        return claims['id_token']['acr']['values']
    except KeyError:
        return None


def should_show_login_form(request):
    two_factor = True if get_acr_claim(request) else False

    user = request.user
    if not user.is_authenticated:
        return True, two_factor

    prompt = get_request_param(request, 'prompt', '').split()
    if 'login' in prompt:
        return True, two_factor

    max_age = get_request_param(request, 'max_age')
    if max_age and not is_recent_auth_time(request, max_age):
        return True, two_factor

    user_has_device = user.device_set.filter(confirmed=True).exists()
    state = get_request_param(request, 'state')
    if two_factor and not user_has_device:
        # TODO: catch error
        raise TwoFactorRequiredError(state=state)
    if two_factor and not user.is_verified:
        return True, two_factor

    return False, two_factor


def validate_and_redirect_to_login(request, two_factor, uri, http_method='GET', body=None, headers=None):
    oidc_server.validate_authorization_request(uri, http_method, body, headers)
    return redirect_to_login(request, two_factor=two_factor)


def get_registered_redirect_uri(request):
    """
    Return the request's redirect_uri only if it is registered for the given
    client_id, otherwise None. Used to avoid an open redirect when an OAuth2Error
    is raised before oauthlib has validated the request (e.g. TwoFactorRequiredError,
    which is raised in should_show_login_form before redirect_uri validation).
    """
    client_id = get_request_param(request, 'client_id')
    redirect_uri = get_request_param(request, 'redirect_uri')
    if not client_id or not redirect_uri:
        return None
    try:
        client = Client.objects.get(uuid=client_id, is_active=True)
    except (Client.DoesNotExist, ValidationError, ValueError):
        return None
    if check_redirect_uri(client, redirect_uri):
        return redirect_uri
    return None


@revision_exempt
@never_cache
@xframe_options_exempt
def authorize(request):
    uri, http_method, body, headers = extract_params(request)
    try:
        login_req, two_factor = should_show_login_form(request)

        if login_req:
            return validate_and_redirect_to_login(request, two_factor, uri, http_method, body, headers)
        else:
            oauth_request = Request(uri, http_method=http_method, body=body, headers=headers)
            scopes = scope_to_list(oauth_request.scope)
            credentials = {
                'user': request.user,
                'session_state': get_oidc_session_state(request),
            }
            headers, _, _ = oidc_server.create_authorization_response(
                uri, http_method, body, headers, scopes, credentials)
            return HttpOAuth2ResponseRedirect(headers['Location'])

    except oauth2.FatalClientError as e:
        logger.warning(f'Fatal client error, redirecting to error page. {e}')
        error_uri = reverse('oauth2:oauth2_error')
        return HttpResponseRedirect(e.in_uri(error_uri))
    except oauth2.OAuth2Error as e:
        # Less grave errors are reported back to the client, but only to a
        # redirect_uri that is actually registered for the client. Otherwise an
        # error raised before oauthlib validated the request (e.g.
        # TwoFactorRequiredError) could be abused for an open redirect.
        logger.warning(f'OAuth2Error, redirecting. {e}')
        redirect_uri = get_registered_redirect_uri(request)
        if redirect_uri is not None:
            return HttpOAuth2ResponseRedirect(e.in_uri(redirect_uri))
        return HttpResponseRedirect(e.in_uri(reverse('oauth2:oauth2_error')))


def _active_client(client_id):
    try:
        return Client.objects.get(uuid=client_id, is_active=True)
    except (Client.DoesNotExist, TypeError, ValueError, ValidationError):
        return None


def _add_device_grant_cors(request, response, client=None):
    # public clients, no cookies and no client secret, so every origin is allowed.
    # gated on the per-client device_authorization_grant opt-in: a packaged TV app
    # (Tizen) sends Origin: file://, which is not https and never a redirect_uri
    if client is not None and client.device_authorization_grant:
        add_cors_header(request.META.get('HTTP_ORIGIN'), None, response, public_cors=True)
    return response


def token(request):
    uri, http_method, body, headers = extract_params(request)
    credentials = {}
    headers, body, status = oidc_server.create_token_response(uri, http_method, body, headers, credentials)
    response = HttpResponse(content=body, status=status)

    for k, v in headers.items():
        response[k] = v

    # oauthlib's CORS headers are only set on a successful token response, only for
    # https origins that match a redirect_uri. device_code polling is a public client
    # with no redirect_uri, and authorization_pending / slow_down are 400s
    if (settings.SSO_DEVICE_AUTHORIZATION_GRANT
            and request.POST.get('grant_type') == DEVICE_CODE_GRANT_TYPE):
        _add_device_grant_cors(request, response, _active_client(request.POST.get('client_id')))

    return response


class TokenView(PreflightMixin, View):
    http_method_names = ['post', 'options']

    @method_decorator(revision_exempt)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return token(request)


def device_authorization_grant_required(view_func):
    # the device authorization grant is behind the feature flag SSO_DEVICE_AUTHORIZATION_GRANT
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not settings.SSO_DEVICE_AUTHORIZATION_GRANT:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper


def device_authorization(request):
    """
    RFC 8628 device_authorization endpoint. oauthlib's DeviceAuthorizationEndpoint
    (device_authorization_endpoint, see oidc_server.py) mints the device_code/user_code
    pair but does not persist them itself -- we do that here once it returns a 200,
    so DeviceCodeGrantEx / OIDCRequestValidator.validate_device_code have a DeviceCode
    row to poll from the token endpoint.
    """
    uri, http_method, body, headers = extract_params(request)
    # oauthlib compares headers["Content-Type"] with "application/x-www-form-urlencoded": a missing
    # header raises KeyError (500) and a parameter like "; charset=utf-8" is rejected, so pass the
    # media type only
    headers = {**headers, 'Content-Type': request.content_type}
    oauth_request = Request(uri, http_method=http_method, body=body, headers=headers)
    client = None
    try:
        resp_headers, data, status = device_authorization_endpoint.create_device_authorization_response(
            uri, http_method=http_method, body=body, headers=headers)
    except oauth2.OAuth2Error as e:
        # e.g. FatalClientError from OIDCRequestValidator._get_client for an unknown client_id
        return HttpResponse(content=e.json, status=e.status_code, content_type='application/json')

    if status == 200:
        try:
            client = Client.objects.get(uuid=oauth_request.client_id, is_active=True)
        except (Client.DoesNotExist, ValueError, ValidationError):
            error = oauth2.InvalidClientError(request=oauth_request)
            return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')

        if not oidc_request_validator.validate_grant_type(
                oauth_request.client_id, DEVICE_CODE_GRANT_TYPE, client, oauth_request):
            error = oauth2.UnauthorizedClientError(request=oauth_request)
            return _add_device_grant_cors(
                request, HttpResponse(content=error.json, status=error.status_code, content_type='application/json'),
                client)

        scopes = scope_to_list(oauth_request.scope) or client.scopes.split()
        # oauthlib's DeviceAuthorizationEndpoint does not validate the requested scopes itself
        if not oidc_request_validator.validate_scopes(oauth_request.client_id, scopes, client, oauth_request):
            error = oauth2.InvalidScopeError(request=oauth_request)
            return _add_device_grant_cors(
                request, HttpResponse(content=error.json, status=error.status_code, content_type='application/json'),
                client)

        DeviceCode.objects.create(
            client=client,
            device_code=data['device_code'],
            user_code=data['user_code'],
            scopes=' '.join(scopes),
            expires_at=timezone.now() + timedelta(seconds=data['expires_in']),
        )

    response = HttpResponse(content=json.dumps(data), status=status, content_type='application/json')
    for k, v in resp_headers.items():
        response[k] = v
    return _add_device_grant_cors(request, response, client)


class DeviceAuthorizationView(PreflightMixin, View):
    http_method_names = ['post', 'options']

    @method_decorator(device_authorization_grant_required)
    @method_decorator(revision_exempt)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return device_authorization(request)


@revision_exempt
@csrf_exempt
def revoke(request):
    uri, http_method, body, headers = extract_params(request)
    headers, body, status = oidc_server.create_revocation_response(uri, http_method=http_method, body=body,
                                                                   headers=headers)
    response = HttpResponse(content=body, status=status)
    for k, v in headers.items():
        response[k] = v
    return response


@revision_exempt
@never_cache
def introspect(request):
    uri, http_method, body, headers = extract_params(request)
    headers, body, status = oidc_server.create_introspect_response(uri, http_method=http_method, body=body,
                                                                   headers=headers)
    response = HttpResponse(content=body, status=status)
    for k, v in headers.items():
        response[k] = v
    return response


@revision_exempt
@never_cache
def tokeninfo(request):
    max_length = 2048
    try:
        if 'access_token' in request.GET:
            oauth2_token = request.GET.get('access_token')
        elif 'id_token' in request.GET:
            oauth2_token = request.GET.get('id_token')
        else:
            raise oauth2.InvalidRequestError("either access_token or id_token required")
        if len(oauth2_token) > max_length:
            raise oauth2.InvalidRequestError("oauth2_token length excceded %d" % max_length)

        parsed = loads_jwt(oauth2_token)
        content = json.dumps(parsed)
        return HttpResponse(content=content, content_type='application/json')

    except oauth2.OAuth2Error as e:
        return HttpResponse(content=e.json, status=e.status_code, content_type='application/json')
    except InvalidTokenError as e:
        error = oauth2.InvalidRequestError(description=force_str(e))
        return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')
    except Exception as e:
        error = oauth2.ServerError(description=force_str(e))
        logger.warning('Exception caught while processing request, %s.' % e)
        return HttpResponse(content=error.json, status=error.status_code)


@never_cache
@login_required
def approval(request):
    """
    View to redirect for installed applications, to get an authorisation code
    """
    state = request.GET.get('state', '')
    code = request.GET.get('code', '')
    return render(request, 'oauth2/approval.html', context={'state': state, 'code': code})


@device_authorization_grant_required
@never_cache
@login_required
def device(request):
    """
    RFC 8628 verification_uri: the second-screen page a user opens (from the TV's
    prompt, or via verification_uri_complete's ?user_code=... if scanned/tapped) to
    confirm or deny the code shown on their TV.
    """
    user_code = normalize_user_code(request.POST.get('user_code') or request.GET.get('user_code') or '')
    invalid_code = _('This code is not valid. Please check the code shown on your device.')
    error = None
    device_code_obj = None

    if user_code:
        try:
            device_code_obj = DeviceCode.objects.select_related('client').get(
                user_code=user_code, status=DeviceCode.STATUS_PENDING)
            client = device_code_obj.client
            if device_code_obj.is_expired:
                device_code_obj = None
                error = _('This code has expired. Please start again on your device.')
            elif not (client.is_active and oidc_request_validator.validate_grant_type(
                    client.client_id, DEVICE_CODE_GRANT_TYPE, client, None)):
                # the client was deactivated or lost the device authorization grant after the code was issued
                device_code_obj = None
                error = invalid_code
        except DeviceCode.DoesNotExist:
            error = invalid_code

    if request.method == 'POST' and device_code_obj:
        # only a pending code can be confirmed or denied, a concurrent request that changed it first wins
        pending_code = DeviceCode.objects.filter(pk=device_code_obj.pk, status=DeviceCode.STATUS_PENDING)
        if 'approve' in request.POST:
            if pending_code.update(user=request.user, otp_device=getattr(request.user, 'otp_device', None),
                                   status=DeviceCode.STATUS_APPROVED):
                return render(request, 'oauth2/device.html', {'approved': True, 'client': device_code_obj.client})
            device_code_obj = None
            error = invalid_code
        elif 'deny' in request.POST:
            if pending_code.update(status=DeviceCode.STATUS_DENIED):
                return render(request, 'oauth2/device.html', {'denied': True})
            device_code_obj = None
            error = invalid_code

    return render(request, 'oauth2/device.html', {
        'user_code': user_code,
        'device_code': device_code_obj,
        'error': error,
    })


@permission_required("oauth2.change_client")
def client_details(request, object_id):
    client = get_object_or_404(Client, pk=object_id)
    data = {
        "client_secret": client.client_secret,
        "application_id": client.application.uuid.hex if client.application else None,
        "client_id": client.uuid.hex,
        "scopes": client.scopes,
        "force_using_pkce": client.force_using_pkce,
        "device_authorization_grant": client.device_authorization_grant,
        "redirect_uris": [uri for uri in client.redirect_uris.split()],
        "post_logout_redirect_uris": [uri for uri in client.post_logout_redirect_uris.split()],
        "type": client.type,
    }
    if client.user:
        data['user_id'] = client.user.uuid.hex

    return JsonHttpResponse(data, request)


class ErrorView(TemplateView):
    template_name = "oauth2/error.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['error'] = get_request_param(self.request, 'error')
        context['error_description'] = get_request_param(self.request, 'error_description')
        return context
