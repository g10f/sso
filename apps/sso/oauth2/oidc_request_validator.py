import base64
import logging
from uuid import UUID

from jwt import InvalidTokenError

from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.encoding import force_bytes
from oauthlib.oauth2 import FatalClientError
from oauthlib.openid.connect.core.request_validator import RequestValidator
from .crypt import loads_jwt
from .models import BearerToken, RefreshToken, AuthorizationCode, Client, check_redirect_uri, CONFIDENTIAL_CLIENTS, \
    CLIENT_RESPONSE_TYPES
from .oidc_token import get_idtoken_finalizer

logger = logging.getLogger(__name__)


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
            try:
                request.client = Client.objects.get(uuid=client_id, is_active=True)
            except ValidationError as e:
                raise FatalClientError(e)
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
            access_token = BearerToken.objects.get(refresh_token__token=refresh_token).access_token
            data = loads_jwt(access_token, options={'verify_signature': False})
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

    def finalize_id_token(self, id_token, token, token_handler, request):
        # Finalize OpenID Connect ID token & Sign or Encrypt.
        return get_idtoken_finalizer()(id_token, token, token_handler, request)

    def validate_silent_authorization(self, request):
        # we have not consent required
        return True

    def validate_silent_login(self, request):
        # We have no option for users to deny silent login
        return True

    def validate_user_match(self, id_token_hint, scopes, claims, request):
        if id_token_hint:
            # https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
            if request.user and request.user.is_authenticated:
                try:
                    # ID Token can be expired
                    id_token = loads_jwt(id_token_hint, options={'verify_exp': False, 'verify_aud': False})
                    if id_token['sub'] == request.user.uuid.hex:
                        return True
                except InvalidTokenError as e:
                    logger.warning(e)
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

    def get_authorization_code_nonce(self, client_id, code, redirect_uri, request):
        return request.nonce
