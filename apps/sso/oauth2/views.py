import json
import logging
from urllib.parse import urlparse, urlunparse, urlsplit, urlunsplit

from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from oauthlib import oauth2
from oauthlib.common import Request
from oauthlib.common import urlencode, urlencoded, quote
from oauthlib.oauth2.rfc6749.utils import scope_to_list
from oauthlib.openid.connect.core.exceptions import LoginRequired

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponseRedirect, HttpResponse, QueryDict
from django.http.response import HttpResponseRedirectBase, Http404
from django.shortcuts import render, get_object_or_404, resolve_url
from django.urls import reverse
from django.utils.crypto import salted_hmac
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri, force_str
from django.views import View
from django.views.decorators.cache import never_cache, cache_page, cache_control
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView
from sso.api.response import JsonHttpResponse, same_origin
from sso.api.views.generic import PreflightMixin
from sso.auth.utils import is_recent_auth_time
from sso.auth.views import TWO_FACTOR_PARAM
from sso.middleware import revision_exempt
from sso.utils.http import get_request_param
from sso.utils.url import get_base_url
from .crypt import loads_jwt
from .keys import get_public_keys, get_certs, get_certs_jwks
from .models import Client
from .oidc_server import oidc_server

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
    headers = request.META
    if 'wsgi.input' in headers:
        del headers['wsgi.input']
    if 'wsgi.errors' in headers:
        del headers['wsgi.errors']
    if 'HTTP_AUTHORIZATION' in headers:
        headers['Authorization'] = headers['HTTP_AUTHORIZATION']
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


@method_decorator(cache_page(60 * 60), name='dispatch')
@method_decorator(vary_on_headers('Origin', 'Accept-Language'), name='dispatch')
class OpenidConfigurationView(PreflightMixin, View):
    http_method_names = ['get', 'options']

    def get(self, request, *args, **kwargs):
        """
        http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
        """
        base_uri = get_base_url(request)  # 'http://10.0.2.2:8000'  # for android local client test
        configuration = {
            "issuer": base_uri,
            "authorization_endpoint": '%s%s' % (base_uri, reverse('oauth2:authorize')),
            "token_endpoint": '%s%s' % (base_uri, reverse('oauth2:token')),
            "userinfo_endpoint": '%s%s' % (base_uri, reverse('api:v2_users_me')),
            "revocation_endpoint": '%s%s' % (base_uri, reverse('oauth2:revoke')),
            "jwks_uri": '%s%s' % (base_uri, reverse('oauth2:jwks')),
            "scopes_supported":
                ['openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture'],
            "response_types_supported":
                ["code", "token", "id_token token", "id_token"],
            "id_token_signing_alg_values_supported":
                ["RS256"],
            "token_endpoint_auth_methods_supported":
                ["client_secret_basic"],
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
    client = get_object_or_404(Client, uuid=client_id)

    for redirect_uri in client.redirect_uris.split():
        if same_origin(redirect_uri, origin):
            return HttpResponse(status=204)
    return Http404()


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
    return salted_hmac(key_salt, data, algorithm=settings.DEFAULT_HASHING_ALGORITHM).hexdigest()


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
        # Less grave errors will be reported back to client
        logger.warning(f'OAuth2Error, redirecting to error page. {e}')
        redirect_uri = get_request_param(request, 'redirect_uri', reverse('oauth2:oauth2_error'))
        return HttpResponseRedirect(e.in_uri(redirect_uri))


def token(request):
    uri, http_method, body, headers = extract_params(request)
    credentials = {}
    headers, body, status = oidc_server.create_token_response(uri, http_method, body, headers, credentials)
    response = HttpResponse(content=body, status=status)

    for k, v in headers.items():
        response[k] = v
    return response


class TokenView(PreflightMixin, View):
    http_method_names = ['post', 'options']

    @method_decorator(revision_exempt)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return token(request)


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


@permission_required("oauth2.change_client")
def client_details(request, object_id):
    client = get_object_or_404(Client, pk=object_id)
    data = {
        "client_secret": client.client_secret,
        "application_id": client.application.uuid.hex if client.application else None,
        "client_id": client.uuid.hex,
        "scopes": client.scopes,
        "force_using_pkce": client.force_using_pkce,
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
