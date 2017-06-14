# -*- coding: utf-8 -*-
import hashlib
import json
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from jwt import InvalidTokenError
from oauthlib import oauth2
from oauthlib.common import urlencode, urlencoded, quote
from six.moves.urllib.parse import urlparse, urlunparse, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponseRedirect, HttpResponse, QueryDict
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import render, get_object_or_404, resolve_url
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str, iri_to_uri, force_text, smart_bytes
from django.views.decorators.cache import never_cache, cache_page, cache_control
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from sso.api.response import JsonHttpResponse
from sso.auth.utils import is_recent_auth_time
from sso.auth.views import TWO_FACTOR_PARAM
from sso.utils.convert import long_to_base64
from sso.utils.http import get_request_param
from sso.utils.url import base_url
from .crypt import loads_jwt
from .models import Client
from .server import server

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


@cache_page(60 * 60)
def openid_configuration(request):
    """
    http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
    """
    base_uri = base_url(request)  # 'http://10.0.2.2:8000'  # for android local client test
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
        "end_session_endpoint": '%s%s' % (base_uri, reverse('accounts:logout')),
        "check_session_iframe": '%s%s' % (base_uri, reverse('oauth2:session')),
        "certs_uri": '%s%s' % (base_uri, reverse('oauth2:certs')),
        "profile_uri": '%s%s' % (base_uri, reverse('accounts:profile')),
    }
    if settings.SSO_SERVICE_DOCUMENTATION:
        configuration['service_documentation'] = settings.SSO_SERVICE_DOCUMENTATION
    return JsonHttpResponse(configuration, request, allow_jsonp=True)


class SessionView(TemplateView):
    @method_decorator(cache_control(max_age=60 * 5))
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SessionView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SessionView, self).get_context_data(**kwargs)
        context['session_cookie_name'] = settings.SESSION_COOKIE_NAME
        return context


class LoginRequiredError(oauth2.OAuth2Error):
    error = 'login_required'
    description = 'The End User is currently not already authenticated.'


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


def get_session_state(client_id, browser_state):
    salt = get_random_string()
    if browser_state is None:
        browser_state = ""
    return hashlib.sha256((client_id + " " + browser_state + " " + salt).encode('utf-8')).hexdigest() + "." + salt


class TwoFactorRequiredError(oauth2.OAuth2Error):
    error = 'two_factor_required'
    description = 'The End User has no "two factor" device.'


def get_acr_claim(request):
    claims = json.loads(get_request_param(request, 'claims', '{}'))
    try:
        return claims['id_token']['acr']['values']
    except KeyError:
        return None


def is_login_required(request, client_state):
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
    if two_factor and not user_has_device:
        raise TwoFactorRequiredError(state=client_state)
    if two_factor and not user.is_verified:
        return True, two_factor

    return False, two_factor


@never_cache
@xframe_options_exempt
def authorize(request):
    uri, http_method, body, headers = extract_params(request)
    error_uri = reverse('oauth2:oauth2_error')
    redirect_uri = None
    try:
        scopes, credentials = server.validate_authorization_request(uri, http_method, body, headers)
        credentials['user'] = request.user
        credentials['session_state'] = get_session_state(credentials['client_id'],
                                                         browser_state=request.session.session_key)
        credentials['client'] = credentials['request'].client
        redirect_uri = credentials.get('redirect_uri')
        prompt = get_request_param(request, 'prompt', '').split()

        # check if the user must login
        login_req, two_factor = is_login_required(request, credentials.get('state'))

        if 'none' in prompt:
            if login_req:
                raise LoginRequiredError(state=credentials.get('state'))
            else:
                id_token = get_request_param(request, 'id_token_hint', '')
                try:
                    parsed = loads_jwt(id_token)
                    if parsed['sub'] != request.user.uuid.hex:
                        raise LoginRequiredError(state=credentials.get('state'))
                except InvalidTokenError as e:  # maybe Token used too late
                    logger.exception(e)
                    raise LoginRequiredError(state=credentials.get('state'))

        if login_req:
            return redirect_to_login(request, two_factor=two_factor)

        # if we are here, the user is already logged in does not need to login again          
        headers, body, status = server.create_authorization_response(uri, http_method, body, headers, scopes,
                                                                     credentials)  # @UnusedVariable
        return HttpOAuth2ResponseRedirect(headers['Location'])
    except oauth2.FatalClientError as e:
        logger.warning('Fatal client error, redirecting to error page.')
        return HttpOAuth2ResponseRedirect(e.in_uri(error_uri))
    except oauth2.OAuth2Error as e:
        logger.warning('Client error, redirecting back to client.')
        if not redirect_uri:
            if getattr(e, 'redirect_uri'):
                redirect_uri = e.redirect_uri
            else:
                redirect_uri = error_uri
        return HttpOAuth2ResponseRedirect(e.in_uri(redirect_uri))


@csrf_exempt
def token(request):
    uri, http_method, body, headers = extract_params(request)
    credentials = {}
    headers, body, status = server.create_token_response(uri, http_method, body, headers, credentials)
    response = HttpResponse(content=body, status=status)
    for k, v in headers.items():
        response[k] = v
    return response


@csrf_exempt
def revoke(request):
    uri, http_method, body, headers = extract_params(request)
    headers, body, status = server.create_revocation_response(uri, http_method=http_method, body=body, headers=headers)
    response = HttpResponse(content=body, status=status)
    for k, v in headers.items():
        response[k] = v
    return response


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
        error = oauth2.InvalidRequestError(description=force_text(e))
        return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')
    except Exception as e:
        error = oauth2.ServerError(description=force_text(e))
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


@cache_page(60 * 60)
def certs(request):
    return JsonHttpResponse({settings.CERTS['default']['uuid']: settings.CERTS['default']['certificate']}, request)


@cache_page(60 * 60)
def jwks(request):
    """
    jwks_uri view (http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata)
    """
    key = load_pem_public_key(smart_bytes(settings.CERTS['default']['public_key']), backend=default_backend())
    public_numbers = key.public_numbers()
    data = {
        "keys": [{
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": settings.CERTS['default']['uuid'],
            "n": long_to_base64(public_numbers.n),
            "e": long_to_base64(public_numbers.e)
        }]
    }
    return JsonHttpResponse(data, request)


@permission_required("oauth2.change_client")
def client_details(request, object_id):
    client = get_object_or_404(Client, pk=object_id)
    data = {
        "auth_uri": request.build_absolute_uri(reverse('oauth2:authorize')),
        "client_secret": client.client_secret,
        "token_uri": request.build_absolute_uri(reverse('oauth2:token')),
        "redirect_uris": [uri for uri in client.redirect_uris.split()],
        "application_id": client.application.uuid.hex if client.application else None,
        "client_id": client.uuid.hex,
        "auth_provider_x509_cert_url": request.build_absolute_uri(reverse('oauth2:certs')),
        "userinfo_uri": request.build_absolute_uri(reverse('api:v1_users_me')),
        "logout_uri": request.build_absolute_uri(reverse('accounts:logout')),
    }
    return JsonHttpResponse(data, request)


class ErrorView(TemplateView):
    template_name = "oauth2/error.html"

    def get_context_data(self, **kwargs):
        context = super(ErrorView, self).get_context_data(**kwargs)
        context['error'] = get_request_param(self.request, 'error')
        return context
