# -*- coding: utf-8 -*-
import time
import json
import urlparse
from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import get_random_string

from oauthlib import oauth2
from oauthlib.oauth2.rfc6749.tokens import random_token_generator
from .models import BearerToken, RefreshToken, AuthorizationCode, Client, check_redirect_uri
from .crypt import loads_jwt, make_jwt

import logging
logger = logging.getLogger(__name__)

SUPPORTED_SCOPES = ['openid', 'profile', 'email', 'offline_access', '']
DEFAULT_SCOPES = ['profile']
MAX_AGE = 3600

def get_domain_from_absolute_uri(abs_uri):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(abs_uri)  # @UnusedVariable
    return netloc

    
def default_token_generator(request, max_age=MAX_AGE, refresh_token=False):
    if refresh_token:
        return random_token_generator(request, refresh_token=True)
    else:
        domain = get_domain_from_absolute_uri(request.uri)
        claim_set = {
            'jti': get_random_string(), 
            'iss': domain,
            'sub': request.user.uuid,  # required
            'aud': request.client.client_id,  # required
            'exp': int(time.time()) + max_age,  # required
            'iat': int(time.time()),  # required
            'scope': ' '.join(request.scopes),  # custom, required
        }
        return make_jwt(claim_set)


# http://openid.net/specs/openid-connect-basic-1_0.html#IDToken
def default_idtoken_generator(request, max_age=MAX_AGE, refresh_token=False):
    """
    The generated id_token contains additionally email, name and roles 
    """
    if refresh_token:
        return random_token_generator(request, refresh_token=True)
    else:
        domain = get_domain_from_absolute_uri(request.uri)
        user = request.user
        claim_set = {
            'iss': domain,
            'sub': user.uuid,
            'aud': request.client.client_id,
            'exp': int(time.time()) + max_age,
            'iat': int(time.time()),
            'email': user.email,  # custom
            'name': user.username,  # custom
        }
        if request.client.application:            
            claim_set['roles'] = ' '.join(user.get_roles_by_app(request.client.application.uuid).values_list('name', flat=True))  # custom
        return make_jwt(claim_set)


class OAuth2RequestValidator(oauth2.RequestValidator):
    # Ordered roughly in order of apperance in the authorization grant flow
    # Pre- and Post-authorization.
    def validate_client_id(self, client_id, request, *args, **kwargs):
        try:
            request.client = Client.objects.get(uuid=client_id)
            return True
        except ObjectDoesNotExist:
            return False
        
    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        # We use the pre registerd default uri
        return check_redirect_uri(client_id, redirect_uri)            

    def get_default_redirect_uri(self, client_id, request, *args, **kwargs):
        return request.client.default_redirect_uri

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        requested_scopes = set(scopes)
        valid_scopes = set(SUPPORTED_SCOPES)
        if requested_scopes.issubset(valid_scopes):
            return True
        else:
            return False
        
    def get_default_scopes(self, client_id, request, *args, **kwargs):
        return DEFAULT_SCOPES

    def validate_response_type(self, client_id, response_type, client, request, *args, **kwargs):
        # currently we support "code" and "token"
        client_type = client.type
        if client_type in ['web', 'native'] and response_type == "code":
            return True
        elif client_type == 'javascript' and response_type == 'token':
            return True
        else:
            return False            
    
    # Post-authorization
    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        # Remember to associate it with request.scopes, request.redirect_uri
        # request.client, request.state and request.user (the last is passed in
        # post_authorization credentials, i.e. { 'user': request.user}.
        client = Client.objects.get(uuid=client_id)
        state = request.state if request.state else ''
        authorization_code = AuthorizationCode(client=client, code=code['code'], user=request.user, 
                                               redirect_uri=request.redirect_uri, state=state, 
                                               scopes=' '.join(request.scopes))
        authorization_code.save()

    # Token request
    def authenticate_client(self, request, *args, **kwargs):
        # Whichever authentication method suits you, HTTP Basic might work
        if request.grant_type in ['client_credentials', 'password']:  
            # http://tools.ietf.org/html/rfc6749#section-4.4
            if 'HTTP_AUTHORIZATION' in request.headers:
                # client credentials grant type
                http_authorization = request.headers['HTTP_AUTHORIZATION'].split(' ')
                if (len(http_authorization) == 2) and http_authorization[0] == 'Basic':
                    request.client_id, request.client_secret = http_authorization[1].decode("base64").split(":")
                
        try:
            request.client = Client.objects.get(uuid=request.client_id, client_secret=request.client_secret)
            if request.grant_type == 'client_credentials':
                if request.client.user:
                    request.user = request.client.user
                    return True
                else:
                    logger.error("missing user for client %s in authenticate_client with grant_type 'client_credentials'", request.client)
            else:
                return True
        except ObjectDoesNotExist:
            pass      
        
        return False

    def authenticate_client_id(self, client_id, request, *args, **kwargs):
        # Don't allow public (non-authenticated) clients
        return False

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        # Validate the code belongs to the client. Add associated scopes,
        # state and user to request.scopes, request.state and request.user.
        try:
            authorization_code = AuthorizationCode.objects.get(code=request.code, client__uuid=client_id, is_valid=True)
            request.user = authenticate(token=authorization_code)
            request.state = authorization_code.state
            request.scopes = authorization_code.scopes.split()  
            return True
        except ObjectDoesNotExist:
            return False        

    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, *args, **kwargs):
        # You did save the redirect uri with the authorization code right?
        try:
            authorization_code = AuthorizationCode.objects.get(code=code, client__uuid=client_id, is_valid=True)
            if (authorization_code.redirect_uri == redirect_uri):
                return True
            else:
                return False
        except ObjectDoesNotExist:
            return False        

    def validate_grant_type(self, client_id, grant_type, client, request, *args, **kwargs):
        # Clients should only be allowed to use one type of grant.
        # In this case, it must be "authorization_code" or "refresh_token"
        client_type = client.type
        if client_type in ['web', 'native'] and grant_type in ["authorization_code", "refresh_token"]:
            return True
        elif client_type == 'service' and grant_type == 'client_credentials':
            return True
        elif client_type == 'trusted' and  grant_type == 'password':
            return True
        else:
            logger.warning("client_type and grant_type combination is invalid (%s, %s)", client_type, grant_type)
            
            return False            

    def save_bearer_token(self, token, request, *args, **kwargs):
        bearer_token = BearerToken.objects.create(client=request.client, access_token=token['access_token'], user=request.user)
        if 'refresh_token' in token:
            RefreshToken.objects.create(
                    token=token['refresh_token'], 
                    bearer_token=bearer_token)
        
    def invalidate_authorization_code(self, client_id, code, request, *args, **kwargs):
        # Authorization codes are use once, invalidate it when a Bearer token
        # has been acquired.
        try:      
            authorization_code = AuthorizationCode.objects.get(code=code, is_valid=True)
            authorization_code.is_valid = False
            authorization_code.save()            
        except ObjectDoesNotExist:
            pass

    # Protected resource request
    def validate_bearer_token(self, token, scopes, request):
        # Remember to check expiration and scope membership
        try:
            if not token:
                return False
            data = loads_jwt(token)
            required_scopes = set(scopes)
            if data.get('scope'):
                valid_scopes = set(data['scope'].split())
                if not required_scopes.issubset(valid_scopes):
                    return False
            else:
                logger.debug('Bearer Token with no scope')
            user = get_user_model().objects.get(uuid=data['sub'])
            request.user = user
            request.client = Client.objects.get(uuid=data['aud'])
        except (ObjectDoesNotExist, signing.BadSignature, ValueError):
            return False
        return True

    # Token refresh request
    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        """
        Ensure the Bearer token is valid and authorized access to scopes.

        OBS! The request.user attribute should be set to the resource owner
        associated with this refresh token.
        """
        try:
            refresh_token = RefreshToken.objects.get(token=refresh_token)            
            request.user = authenticate(token=refresh_token)            
        except RefreshToken.DoesNotExist:
            return False
        return True
    
    # Token refresh request
    def get_original_scopes(self, refresh_token, request, *args, **kwargs):
        # Obtain the token associated with the given refresh_token and
        # return its scopes, these will be passed on to the refreshed
        # access token if the client did not specify a scope during the
        # request.
        try:
            data = loads_jwt(BearerToken.objects.get(refresh_token__token=refresh_token).access_token)
            request.scopes = data['scope'].split()
            return True
        except Exception, e:
            logger.error('confirm_scopes Error: %s' % e)
            return False
        
    def validate_user(self, username, password, client, request, *args, **kwargs):
        # legacy client's can use grant_type=password
        # http://tools.ietf.org/html/rfc6749#section-4.3
        user = authenticate(username=username, password=password)
        if user:
            request.user = user
            return True
        return False
    

class OpenIDConnectBearerToken(oauth2.BearerToken):
    """
    Bearer token with OpenIDConnect id_token where the access token is equal the id_token
    """

    def __init__(self, request_validator=None):
        super(OpenIDConnectBearerToken, self).__init__(request_validator, token_generator=default_token_generator)
        self.idtoken_generator = default_idtoken_generator

    def create_token(self, request, refresh_token=False):
        """Create a BearerToken, without refresh token and with an id_token."""
        token = {
            'access_token': self.token_generator(request),
            'expires_in': self.expires_in,
            'token_type': 'Bearer',
        }
        if request.scopes is not None:
            token['scope'] = ' '.join(request.scopes)
            if 'openid' in request.scopes:
                token['id_token'] = self.idtoken_generator(request)
                
        if request.state is not None:
            token['state'] = request.state

        if refresh_token:
            token['refresh_token'] = self.token_generator(request, refresh_token=True)

        token.update(request.extra_credentials or {})

        self.request_validator.save_bearer_token(token, request)
        return token

 
class OpenIDConnectAuthorizationCodeGrant(oauth2.AuthorizationCodeGrant):
    def create_token_response(self, request, token_handler):
        """
        Same functionality as in AuthorizationCodeGrant, except that
        refresh_token is only true if offline_access is in scope
        """
        headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Cache-Control': 'no-store',
                'Pragma': 'no-cache',
        }
        try:
            self.validate_token_request(request)
            logger.debug('Token request validation ok for %r.', request)
        except oauth2.OAuth2Error as e:
            logger.debug('Client error during validation of %r. %r.', request, e)
            return headers, e.json, e.status_code
        
        # see http://openid.net/specs/openid-connect-basic-1_0.html#scopes
        refresh_token = 'offline_access' in request.scopes
        token = token_handler.create_token(request, refresh_token=refresh_token)
        self.request_validator.invalidate_authorization_code(
                request.client_id, request.code, request)
        return headers, json.dumps(token), 200


class OAuthServer(oauth2.AuthorizationEndpoint, oauth2.TokenEndpoint, oauth2.ResourceEndpoint):
    """An  endpoint featuring authorization code and implicit grant types."""

    def __init__(self, request_validator, *args, **kwargs):
        auth_grant = OpenIDConnectAuthorizationCodeGrant(request_validator)
        bearer = OpenIDConnectBearerToken(request_validator)
        refresh_grant = oauth2.RefreshTokenGrant(request_validator)
        implicit_grant = oauth2.ImplicitGrant(request_validator)
        client_credentials = oauth2.ClientCredentialsGrant(request_validator)
        resource_owner_password_credentials = oauth2.ResourceOwnerPasswordCredentialsGrant(request_validator)
        oauth2.AuthorizationEndpoint.__init__(self, default_response_type='code',
                response_types={
                    'code': auth_grant,
                    'token': implicit_grant,
                },
                default_token_type=bearer)
        oauth2.TokenEndpoint.__init__(self, default_grant_type='authorization_code',
                grant_types={
                    'authorization_code': auth_grant,
                    'refresh_token': refresh_grant,
                    'client_credentials': client_credentials,
                    'password': resource_owner_password_credentials,
                },
                default_token_type=bearer)
        oauth2.ResourceEndpoint.__init__(self, default_token='Bearer',
                token_types={'Bearer': bearer})


server = OAuthServer(OAuth2RequestValidator())
