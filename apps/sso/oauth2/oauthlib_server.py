import base64
import calendar
import json
import logging
import time
from urllib.parse import urlsplit
from uuid import UUID

from jwt import InvalidTokenError

from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text, force_bytes
from oauthlib.oauth2.rfc6749 import errors
from oauthlib.oauth2.rfc6749 import tokens
from oauthlib.oauth2.rfc6749.endpoints import AuthorizationEndpoint, RevocationEndpoint, TokenEndpoint
from oauthlib.oauth2.rfc6749.endpoints.introspect import IntrospectEndpoint
from oauthlib.oauth2.rfc6749.grant_types import AuthorizationCodeGrant as OAuth2AuthorizationCodeGrant, \
    ImplicitGrant as OAuth2ImplicitGrant, ClientCredentialsGrant, RefreshTokenGrant, \
    ResourceOwnerPasswordCredentialsGrant
from oauthlib.openid.connect.core.grant_types import ImplicitGrant, GrantTypeBase
from oauthlib.openid.connect.core.grant_types.dispatchers import AuthorizationCodeGrantDispatcher, \
    ImplicitTokenGrantDispatcher, AuthorizationTokenGrantDispatcher
from oauthlib.openid.connect.core.request_validator import RequestValidator
from sso.api.response import add_cors_header
from sso.auth import get_session_auth_hash, HASH_SESSION_KEY
from .crypt import loads_jwt, make_jwt, MAX_AGE
from .models import BearerToken, RefreshToken, AuthorizationCode, Client, check_redirect_uri, CONFIDENTIAL_CLIENTS, \
    CLIENT_RESPONSE_TYPES

logger = logging.getLogger(__name__)


# SUPPORTED_SCOPES = ['openid', 'profile', 'email', 'offline_access', 'address', 'phone']
# DEFAULT_SCOPES = ['openid', 'profile']


def get_iss_from_absolute_uri(abs_uri):
    (scheme, netloc, path, query, fragment) = urlsplit(abs_uri)  # @UnusedVariable
    return "%s://%s" % (scheme, netloc)


def default_token_generator(request, max_age=MAX_AGE):
    user = request.user
    claim_set = {
        'jti': get_random_string(),
        'iss': get_iss_from_absolute_uri(request.uri),
        'sub': user.uuid.hex,  # required
        'aud': request.client.client_id,  # required
        'exp': int(time.time()) + max_age,  # required
        'iat': int(time.time()),  # required
        'acr': '1' if user.is_verified else '0',
        'scope': ' '.join(request.scopes),  # custom, required
        'email': force_text(user.primary_email()),  # custom
        'name': user.username,  # custom
        # session authentication hash,
        HASH_SESSION_KEY: get_session_auth_hash(user, request.client),  # custom, required
    }
    if request.client.application:
        claim_set['roles'] = ' '.join(
            user.get_roles_by_app(request.client.application.uuid).values_list('name', flat=True))  # custom
    return make_jwt(claim_set)


# http://openid.net/specs/openid-connect-basic-1_0.html#IDToken
def default_idtoken_generator(request, max_age=MAX_AGE):
    """
    The generated id_token contains additionally email, name and roles
    """
    user = request.user
    auth_time = int(calendar.timegm(user.last_login.utctimetuple()))
    claim_set = {
        'iss': get_iss_from_absolute_uri(request.uri),
        'sub': user.uuid.hex,
        'aud': request.client.client_id,
        'exp': int(time.time()) + max_age,
        'iat': int(time.time()),
        'auth_time': auth_time,  # required when max_age is in the request
        'acr': '1' if user.is_verified else '0',
        'email': force_text(user.primary_email()),  # custom
        'name': user.username,  # custom
        'given_name': user.first_name,  # custom
        'family_name': user.last_name,  # custom
    }
    if request.nonce:
        claim_set['nonce'] = request.nonce  # required if provided by the client
    if request.client.application:
        claim_set['roles'] = ' '.join(
            user.get_roles_by_app(request.client.application.uuid).values_list('name', flat=True))  # custom
    return make_jwt(claim_set)


def get_client_id_and_secret_from_auth_header(request):
    if 'HTTP_AUTHORIZATION' in request.headers:
        # client credentials grant type
        http_authorization = request.headers['HTTP_AUTHORIZATION'].split(' ')
        if (len(http_authorization) == 2) and http_authorization[0] == 'Basic':
            data = base64.b64decode(force_bytes(http_authorization[1])).decode()
            return data.split(':')


class OIDCRequestValidator(RequestValidator):
    def _get_client(self, client_id, request):
        if request.client:
            assert (request.client.uuid == UUID(client_id))
        else:
            request.client = Client.objects.get(uuid=client_id, is_active=True)
        return request.client

    def is_pkce_required(self, client_id, request):
        client = self._get_client(client_id, request)
        return client.force_using_pkce

    def get_code_challenge(self, code, request):
        return request.client.authorization_code.code_challenge or None

    def get_code_challenge_method(self, code, request):
        return request.client.authorization_code.code_challenge_method or None

    def get_jwt_bearer_token(self, token, token_handler, request):
        raise NotImplementedError()

    def validate_jwt_bearer_token(self, token, scopes, request):
        raise NotImplementedError()

    def validate_id_token(self, token, scopes, request):
        raise NotImplementedError()

    def introspect_token(self, token, token_type_hint, request, *args, **kwargs):
        try:
            refresh_token = RefreshToken.objects.get(token=token)
            return {'active': True, 'username': refresh_token.user.username, 'token_type': 'refresh_token'}
        except RefreshToken.DoesNotExist:
            pass

        try:
            data = loads_jwt(token)
            data.update({'token_type': 'access_token'})
            return data
        except (InvalidTokenError, NotImplementedError):
            pass

        return None

    # Ordered roughly in order of appearance in the authorization grant flow
    # Pre- and Post-authorization.
    def validate_client_id(self, client_id, request, *args, **kwargs):
        try:
            self._get_client(client_id, request)
            return True
        except (ObjectDoesNotExist, ValueError, ValidationError):
            logger.warning("validate_client_id failed for client_id: %s", client_id)
            return False

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        # We use the pre registered default uri
        client = self._get_client(client_id, request)
        return check_redirect_uri(client, redirect_uri)

    def get_default_redirect_uri(self, client_id, request, *args, **kwargs):
        return request.client.default_redirect_uri

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        requested_scopes = set(scopes)
        valid_scopes = set(client.scopes.split())
        if requested_scopes.issubset(valid_scopes):
            return True
        else:
            return False

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        client = self._get_client(client_id, request)
        return client.scopes.split()

    def validate_response_type(self, client_id, response_type, client, request, *args, **kwargs):
        # currently we support "code", "token" and "id_token token"
        return response_type in CLIENT_RESPONSE_TYPES[client.type]

    # Post-authorization
    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        # Remember to associate it with request.scopes, request.redirect_uri
        # request.client, request.state and request.user (the last is passed in
        # post_authorization credentials, i.e. { 'user': request.user}.
        self._get_client(client_id, request)
        client = request.client
        nonce = request.nonce or ''
        state = request.state or ''

        code_challenge = request.code_challenge or ''
        if code_challenge:
            code_challenge_method = request.code_challenge_method or 'plain'
        else:
            code_challenge_method = ''

        otp_device = getattr(request.user, 'otp_device', None)
        authorization_code = AuthorizationCode(client=client, code=code['code'], user=request.user,
                                               otp_device=otp_device, redirect_uri=request.redirect_uri, state=state,
                                               scopes=' '.join(request.scopes), code_challenge=code_challenge,
                                               code_challenge_method=code_challenge_method, nonce=nonce)
        authorization_code.save()

    # Token request
    def authenticate_client(self, request, *args, **kwargs):
        # is called for confidential clients
        # Whichever authentication method suits you, HTTP Basic might work
        if request.grant_type in ['client_credentials', 'password', 'refresh_token']:
            # http://tools.ietf.org/html/rfc6749#section-4.4
            if 'HTTP_AUTHORIZATION' in request.headers:
                request.client_id, request.client_secret = get_client_id_and_secret_from_auth_header(request)
        try:
            # 1. check the client_id
            client = self._get_client(request.client_id, request)
            # 2. check client_secret
            if client.client_secret != request.client_secret:
                raise ObjectDoesNotExist('client_secret does not match')

            # 3. check that a user is associated to the client for grant_type == 'client_credentials'
            if request.grant_type == 'client_credentials':
                user = request.client.user
                if user:
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    request.user = user
                    return True
                else:
                    logger.error(
                        "missing user for client %s in authenticate_client with grant_type 'client_credentials'",
                        request.client)
            else:
                return True
        except (ObjectDoesNotExist, ValueError):
            logger.warning("authenticate_client failed for client_id: %s", request.client_id, exc_info=True)
            pass

        return False

    def authenticate_client_id(self, client_id, request, *args, **kwargs):
        # is called for non-confidential clients
        # Ensure client_id belong to a non-confidential client.
        client = self._get_client(client_id, request)
        if client.type in CONFIDENTIAL_CLIENTS:
            return False
        else:
            request.client_id = client_id
            return True

    def validate_code(self, client_id, code, client, request, *args, **kwargs):
        # Validate the code belongs to the client. Add associated scopes
        # and user to request.scopes and request.user.
        try:
            if not hasattr(client, 'authorization_code'):
                # save the authorization_code for using in confirm_redirect_uri
                client.authorization_code = AuthorizationCode.objects.get(code=request.code, client__uuid=client_id,
                                                                          is_valid=True)
            authorization_code = client.authorization_code
            request.user = authenticate(token=authorization_code)
            request.scopes = authorization_code.scopes.split()
            request.nonce = authorization_code.nonce

            return True
        except ObjectDoesNotExist:
            return False

    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, *args, **kwargs):
        # You did save the redirect uri with the authorization code right?
        try:
            authorization_code = client.authorization_code
            # AuthorizationCode.objects.get(code=code, client__uuid=client_id, is_valid=True)
            if authorization_code.redirect_uri == redirect_uri:
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
        elif client_type == 'trusted' and grant_type == 'password':
            return True
        else:
            logger.warning("client_type and grant_type combination is invalid (%s, %s)", client_type, grant_type)

            return False

    def save_bearer_token(self, token, request, *args, **kwargs):
        if 'access_token' in token:
            bearer_token = BearerToken.objects.create(client=request.client, access_token=token['access_token'],
                                                      user=request.user)
            if 'refresh_token' in token:
                otp_device = getattr(request.user, 'otp_device', None)
                RefreshToken.objects.create(token=token['refresh_token'],
                                            bearer_token=bearer_token)  # , otp_device=otp_device)

    def invalidate_authorization_code(self, client_id, code, request, *args, **kwargs):
        # Authorization codes are used once, invalidate it when a Bearer token
        # has been acquired.
        AuthorizationCode.objects.filter(code=code, is_valid=True).update(is_valid=False)

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
            request.client = Client.objects.get(uuid=data['aud'], is_active=True)
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
            data = loads_jwt(BearerToken.objects.get(refresh_token__token=refresh_token).access_token, verify=False)
            return data['scope'].split()
        except Exception as e:
            logger.error('confirm_scopes Error: %s' % e)
            return []

    def validate_user(self, username, password, client, request, *args, **kwargs):
        # legacy client's can use grant_type=password
        # http://tools.ietf.org/html/rfc6749#section-4.3
        user = authenticate(username=username, password=password)
        if user:
            request.user = user
            return True
        return False

    def client_authentication_required(self, request, *args, **kwargs):
        if not request.client_id:
            if 'HTTP_AUTHORIZATION' in request.headers:
                # client credentials grant type
                request.client_id, request.client_secret = get_client_id_and_secret_from_auth_header(request)

        client = self._get_client(request.client_id, request)
        if client.type in CONFIDENTIAL_CLIENTS:
            return True
        else:
            return False

    def revoke_token(self, token, token_type_hint, request, *args, **kwargs):
        RefreshToken.objects.filter(token=token).delete()

    def get_id_token(self, token, token_handler, request):
        # the request.scope should be used by the get_id_token() method to determine which claims to include in
        # the resulting id_token
        return default_idtoken_generator(request)

    def validate_silent_authorization(self, request):
        # We have no consent dialog
        raise True

    def validate_silent_login(self, request):
        # Todo: move logic with 'none' in prompt from authorize and TEST
        raise NotImplementedError('Subclasses must implement this method.')

    def validate_user_match(self, id_token_hint, scopes, claims, request):
        #  TODO: Test
        if id_token_hint:
            if request.user is not None and request.user.uuid == id_token_hint:
                return True
            return False
        return True

    def get_authorization_code_scopes(self, client_id, code, redirect_uri, request):
        # Validate the code belongs to the client. Add associated scopes
        # and user to request.scopes and request.user.
        try:
            request.scopes = ()
            authorization_code = AuthorizationCode.objects.get(code=request.code, is_valid=True)

            if client_id:
                if authorization_code.client.uuid == UUID(client_id):
                    client = self._get_client(client_id, request)
                    # check if code belongs to client
                    # save the authorization_code for using later
                    client.authorization_code = authorization_code
                    request.scopes = authorization_code.scopes.split()
                    request.user = authorization_code.user
                else:
                    logger.warning("authorization code does not belong to client")
            else:
                # client is authenticating client_id is not required https://tools.ietf.org/html/rfc6749#page-29
                request.scopes = authorization_code.scopes.split()
        except ObjectDoesNotExist:
            logger.warning("authorization code not found")
        return request.scopes


class OAuth2AuthorizationCodeGrantEx(OAuth2AuthorizationCodeGrant):
    def create_token_response(self, request, token_handler):
        headers = self._get_default_headers()
        try:
            self.validate_token_request(request)
            logger.debug('Token request validation ok for %r.', request)
        except errors.OAuth2Error as e:
            logger.debug('Client error during validation of %r. %r.', request, e)
            headers.update(e.headers)
            return headers, e.json, e.status_code

        # custom extension of original oauthlib: we only deliver refresh_tokens with scope 'offline_access'
        refresh_token = 'offline_access' in request.scopes

        token = token_handler.create_token(request, refresh_token=refresh_token)
        for modifier in self._token_modifiers:
            token = modifier(token, token_handler, request)
        self.request_validator.save_token(token, request)
        self.request_validator.invalidate_authorization_code(
            request.client_id, request.code, request)
        # custom extension of original oauthlib
        if request.client and request.client.type not in CONFIDENTIAL_CLIENTS and 'HTTP_ORIGIN' in request.headers:
            origin = request.headers['HTTP_ORIGIN']
            add_cors_header(origin, request.client, headers)
        return headers, json.dumps(token), 200


class AuthorizationCodeGrantEx(GrantTypeBase):

    def __init__(self, request_validator=None, **kwargs):
        # custom proxy_target
        self.proxy_target = OAuth2AuthorizationCodeGrantEx(request_validator=request_validator, **kwargs)
        self.custom_validators.post_auth.append(self.openid_authorization_validator)
        self.register_token_modifier(self.add_id_token)


class HybridGrantEx(GrantTypeBase):
    def __init__(self, request_validator=None, **kwargs):
        self.request_validator = request_validator or RequestValidator()
        # custom proxy_target
        self.proxy_target = OAuth2AuthorizationCodeGrantEx(request_validator=request_validator, **kwargs)
        # All hybrid response types should be fragment-encoded.
        self.proxy_target.default_response_mode = "fragment"
        self.register_response_type('code id_token')
        self.register_response_type('code token')
        self.register_response_type('code id_token token')
        self.custom_validators.post_auth.append(self.openid_authorization_validator)
        # Hybrid flows can return the id_token from the authorization
        # endpoint as part of the 'code' response
        self.register_code_modifier(self.add_token)
        self.register_code_modifier(self.add_id_token)
        self.register_token_modifier(self.add_id_token)


class Server(AuthorizationEndpoint, IntrospectEndpoint, TokenEndpoint, RevocationEndpoint):
    """ An all-in-one endpoint  see oauthlib.openid.connect.core.endpoints.pre_configured """

    def __init__(self, request_validator, token_expires_in=None, token_generator=None, refresh_token_generator=None,
                 *args, **kwargs):
        auth_grant_ex = OAuth2AuthorizationCodeGrantEx(request_validator)
        implicit_grant = OAuth2ImplicitGrant(request_validator)
        password_grant = ResourceOwnerPasswordCredentialsGrant(request_validator)
        credentials_grant = ClientCredentialsGrant(request_validator)
        refresh_grant = RefreshTokenGrant(request_validator)
        openid_connect_auth_ex = AuthorizationCodeGrantEx(request_validator)
        openid_connect_implicit = ImplicitGrant(request_validator)
        openid_connect_hybrid_ex = HybridGrantEx(request_validator)

        bearer = tokens.BearerToken(request_validator, token_generator, token_expires_in, refresh_token_generator)
        auth_grant_choice = AuthorizationCodeGrantDispatcher(default_grant=auth_grant_ex,
                                                             oidc_grant=openid_connect_auth_ex)
        implicit_grant_choice = ImplicitTokenGrantDispatcher(default_grant=implicit_grant,
                                                             oidc_grant=openid_connect_implicit)

        AuthorizationEndpoint.__init__(self, default_response_type='code',
                                       response_types={
                                           'code': auth_grant_choice,
                                           'token': implicit_grant_choice,
                                           'id_token': openid_connect_implicit,
                                           'id_token token': openid_connect_implicit,
                                           'code token': openid_connect_hybrid_ex,
                                           'code id_token': openid_connect_hybrid_ex,
                                           'code id_token token': openid_connect_hybrid_ex,
                                           'none': auth_grant_ex
                                       },
                                       default_token_type=bearer)

        token_grant_choice = AuthorizationTokenGrantDispatcher(request_validator, default_grant=auth_grant_ex,
                                                               oidc_grant=openid_connect_auth_ex)

        TokenEndpoint.__init__(self, default_grant_type='authorization_code',
                               grant_types={
                                   'authorization_code': token_grant_choice,
                                   'password': password_grant,
                                   'client_credentials': credentials_grant,
                                   'refresh_token': refresh_grant,
                               },
                               default_token_type=bearer)
        RevocationEndpoint.__init__(self, request_validator)
        IntrospectEndpoint.__init__(self, request_validator)


oidc_request_validator = OIDCRequestValidator()
oidc_server = Server(oidc_request_validator, token_generator=default_token_generator,
                     refresh_token_generator=tokens.random_token_generator)
