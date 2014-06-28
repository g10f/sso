# -*- coding: utf-8 -*-
import json
import base64
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404
from oauthlib import oauth2
from oauthlib.common import urlencode

from http.http_status import *  # @UnusedWildImport
from sso.oauth2.decorators import login_required
from utils.url import base_url
from utils.convert import pack_bigint
from sso.api.response import JsonHttpResponse 
from .crypt import key, loads_jwt, BadSignature
from .server import server
from .models import Client

import logging

logger = logging.getLogger(__name__)

def extract_params(request):
    logger.debug('Extracting parameters from request.')
    uri = request.build_absolute_uri()
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


class HttpOAuth2ResponseRedirect(HttpResponseRedirect):
    """
    handle the special case of locally installed clients, which can send urn:ietf:wg:oauth:2.0:oob
    as the redirect uri. This uri gets mapped to a uri of this identity provider
    """
    allowed_schemes = ['http', 'https']

    def __init__(self, redirect_to, *args, **kwargs):
        if redirect_to.startswith('urn:ietf:wg:oauth:2.0:oob'):
            redirect_to = redirect_to.replace('urn:ietf:wg:oauth:2.0:oob', reverse('oauth2:approval'), 1)
            
        super(HttpOAuth2ResponseRedirect, self).__init__(redirect_to, *args, **kwargs)


@cache_page(60 * 60)
def openid_configuration(request):
    """
    http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
    """
    base_uri = base_url(request)
    configuration = {
        "issuer": base_uri,
        "authorization_endpoint": '%s%s' % (base_uri, reverse('oauth2:authorize')),
        "token_endpoint": '%s%s' % (base_uri, reverse('oauth2:token')),
        "userinfo_endpoint": '%s%s' % (base_uri, reverse('api:v1_users_me')),
        "jwks_uri": '%s%s' % (base_uri, reverse('oauth2:jwks')),
        "scopes_supported": 
            ["openid", "profile", "email", "address", "phone", "offline_access"],
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
        "service_documentation":
            "https://wiki.dwbn.org/general/AccessAndIdentityManagement",
        "logout_uri": '%s%s' % (base_uri, reverse('accounts:logout')),
        "certs_uri": '%s%s' % (base_uri, reverse('oauth2:certs')),
        "profile_uri": '%s%s' % (base_uri, reverse('accounts:profile'))
    }
    return JsonHttpResponse(configuration, request)
    

@login_required
@never_cache
def authorize(request):
    uri, http_method, body, headers = extract_params(request)
    error_uri = reverse('oauth2:oauth2_error')
    redirect_uri = None
    try:
        scopes, credentials = server.validate_authorization_request(uri, http_method, body, headers)
        credentials['user'] = request.user
        credentials['client'] = credentials['request'].client
        redirect_uri = credentials.get('redirect_uri')
        headers, body, status = server.create_authorization_response(uri, http_method, body, headers, scopes, credentials)  # @UnusedVariable
        return HttpOAuth2ResponseRedirect(headers['Location'])
    except oauth2.FatalClientError as e:
        logger.debug('Fatal client error, redirecting to error page.')
        return HttpOAuth2ResponseRedirect(e.in_uri(error_uri))
    except oauth2.OAuth2Error as e:
        logger.debug('Client error, redirecting back to client.')
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


@never_cache
def tokeninfo(request):
    max_length = 2048
    try:
        if 'access_token' in request.GET:
            token = request.GET.get('access_token')
        elif 'id_token' in request.GET:
            token = request.GET.get('id_token')
        else:
            raise oauth2.InvalidRequestError("either access_token or id_token required")
        if len(token) > max_length:
            raise oauth2.InvalidRequestError("token length excceded %d" % max_length)
            
        parsed = loads_jwt(token)
        content = json.dumps(parsed) 
        return HttpResponse(content=content, content_type='application/json')

    except oauth2.OAuth2Error as e:
        return HttpResponse(content=e.json, status=e.status_code, content_type='application/json')
    except BadSignature as e:
        error = oauth2.InvalidRequestError(description=str(e))
        return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')
    except Exception as e:
        error = oauth2.ServerError(description=str(e))
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
    return render(request, 'oauth2/approval.html', dictionary={'state': state, 'code': code})


@cache_page(60 * 60)
def certs(request):
    return JsonHttpResponse({key.id: key.cert}, request)


@cache_page(60 * 60)
def jwks(request):
    """
    jwks_uri view (http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderMetadata)
    """
    data = {
        "keys": [{
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": key.id,
            "n": base64.b64encode(pack_bigint(key.rsa.key.n)),
            "e": base64.b64encode(pack_bigint(key.rsa.key.e))
        }]
    }
    return JsonHttpResponse(data, request)

@permission_required("oauth2.change_client")
def client_details(request, object_id):
    client = get_object_or_404(Client, pk=object_id)
    content = {
        "auth_uri": request.build_absolute_uri(reverse('oauth2:authorize')),
        "client_secret": client.client_secret,
        "token_uri": request.build_absolute_uri(reverse('oauth2:token')),
        "redirect_uris": [uri for uri in client.redirect_uris.split()],
        "application_id": client.application.uuid if client.application else None,
        "client_id": client.uuid,
        "auth_provider_x509_cert_url": request.build_absolute_uri(reverse('oauth2:certs')),
        "userinfo_uri": request.build_absolute_uri(reverse('api:v1_users_me')),
        "logout_uri": request.build_absolute_uri(reverse('accounts:logout')),
    }
    return JsonHttpResponse(content, request)

class ErrorView(TemplateView):
    template_name = "oauth2/error.html"
    
    def get_context_data(self, **kwargs):
        context = super(ErrorView, self).get_context_data(**kwargs)
        context['error'] = self.request.REQUEST.get('error')
        return context
