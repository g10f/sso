import json
import logging

from oauthlib.oauth2 import InvalidRequestError
from oauthlib.oauth2 import RefreshTokenGrant as OAuth2RefreshTokenGrant
from oauthlib.oauth2.rfc6749 import errors
from oauthlib.oauth2.rfc6749.grant_types import AuthorizationCodeGrant as OAuth2AuthorizationCodeGrant
from oauthlib.oauth2.rfc8628.grant_types.device_code import DeviceCodeGrant as OAuth2DeviceCodeGrant
from oauthlib.openid import RequestValidator
from oauthlib.openid.connect.core.grant_types import GrantTypeBase

from django.conf import settings

logger = logging.getLogger(__name__)


def ascii_only_code_challenge_method(method):
    # oauthlib >= 4 compares code_verifier and code_challenge with hmac.compare_digest, which raises
    # TypeError for non-ASCII strings. RFC 7636 only allows ASCII characters for both, so reject
    # anything else as a failed verification instead of ending in a 500.
    def wrapper(verifier, challenge):
        return verifier.isascii() and challenge.isascii() and method(verifier, challenge)
    return wrapper


class OAuth2RefreshTokenGrantEx(OAuth2RefreshTokenGrant):
    def create_authorization_response(self, request, token_handler):
        raise NotImplementedError('Refresh grant does not implement authorizaation response ')

    def create_token_response(self, request, token_handler):
        headers = self._get_default_headers()
        try:
            logger.debug('Validating refresh token request, %r.', request)
            self.validate_token_request(request)
        except errors.OAuth2Error as e:
            logger.debug('Client error in token request, %s.', e)
            headers.update(e.headers)
            return headers, e.json, e.status_code

        token = token_handler.create_token(request, refresh_token=self.issue_new_refresh_tokens)

        for modifier in self._token_modifiers:
            # added token_handler and request to modifier arguments, so that we can use add_id_token from GrantTypeBase
            token = modifier(token, token_handler, request)

        self.request_validator.save_token(token, request)

        logger.debug('Issuing new token to client id %r (%r), %r.', request.client_id, request.client, token)
        headers.update(self._create_cors_headers(request))
        return headers, json.dumps(token), 200


class OAuth2AuthorizationCodeGrantEx(OAuth2AuthorizationCodeGrant):
    _code_challenge_methods = {name: ascii_only_code_challenge_method(method)
                               for name, method in OAuth2AuthorizationCodeGrant._code_challenge_methods.items()}

    def __init__(self, request_validator=None, **kwargs):
        super().__init__(request_validator, **kwargs)
        self.register_code_modifier(self.add_session_state)

    def add_session_state(self, token, token_handler, request):
        try:
            token['session_state'] = request.session_state
        except AttributeError as e:
            logger.exception(e)
        return token

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
        headers.update(self._create_cors_headers(request))
        return headers, json.dumps(token), 200


class RefreshTokenGrantEx(GrantTypeBase):
    def __init__(self, request_validator=None, **kwargs):
        # overwrite with custom proxy_target
        self.proxy_target = OAuth2RefreshTokenGrantEx(request_validator=request_validator, **kwargs)
        self.register_token_modifier(self.add_id_token)

    def add_id_token(self, token, token_handler, request):
        # if not request.scopes or 'openid' not in request.scopes:
        return super().add_id_token(token, token_handler, request)


class AuthorizationCodeGrantEx(GrantTypeBase):
    # same as AuthorizationCodeGrant from openid, only self.proxy_target is different
    def __init__(self, request_validator=None, **kwargs):
        # overwrite with custom proxy_target
        self.proxy_target = OAuth2AuthorizationCodeGrantEx(request_validator=request_validator, **kwargs)
        self.custom_validators.post_auth.append(self.openid_authorization_validator)
        self.register_token_modifier(self.add_id_token)

    def add_id_token(self, token, token_handler, request):
        if not request.scopes or 'openid' not in request.scopes:
            return token

        nonce = self.request_validator.get_authorization_code_nonce(request.client_id, request.code,
                                                                    request.redirect_uri, request
                                                                    )
        return super().add_id_token(token, token_handler, request, nonce=nonce)


class HybridGrantEx(GrantTypeBase):
    def __init__(self, request_validator=None, **kwargs):
        self.request_validator = request_validator or RequestValidator()

        # overwrite with custom proxy_target
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

    def openid_authorization_validator(self, request):
        request_info = super().openid_authorization_validator(request)
        if not request_info:  # returns immediately if OAuth2.0
            return request_info

        if request.response_type in ["code id_token", "code id_token token"]:
            if not request.nonce:
                raise InvalidRequestError(request=request, description='Request is missing mandatory nonce parameter.')
        return request_info


class OAuth2DeviceCodeGrantEx(OAuth2DeviceCodeGrant):
    """
    RFC 8628 Device Authorization Grant, for public clients with no keyboard (TVs) or no
    browser to redirect through (CLIs).

    oauthlib's DeviceCodeGrant authenticates the client and validates grant type and scopes,
    but does not check the device_code itself: no lookup, no polling semantics
    (authorization_pending / slow_down / expired_token / access_denied) and no handoff from
    the verification page. This is delegated to OIDCRequestValidator.validate_device_code().
    """
    def validate_token_request(self, request):
        # feature flag, see views.device_authorization_grant_required
        if not settings.SSO_DEVICE_AUTHORIZATION_GRANT:
            raise errors.UnsupportedGrantTypeError(request=request)
        super().validate_token_request(request)

        if not getattr(request, 'device_code', None):
            raise errors.InvalidRequestError(description='Missing device_code parameter.', request=request)
        device_code = self.request_validator.validate_device_code(request.client_id, request.device_code, request)

        # the scopes and user approved on the verification page
        request.user = device_code.user
        request.scopes = device_code.scopes.split()

    def create_token_response(self, request, token_handler):
        headers = self._get_default_headers()
        try:
            self.validate_token_request(request)
        except errors.OAuth2Error as e:
            logger.debug('Client error during device_code token request: %r.', e)
            headers.update(e.headers)
            return headers, e.json, e.status_code

        # custom extension of original oauthlib: we only deliver refresh_tokens with scope 'offline_access'
        token = token_handler.create_token(request, refresh_token='offline_access' in request.scopes)
        for modifier in self._token_modifiers:
            token = modifier(token, token_handler, request)
        self.request_validator.save_token(token, request)

        headers.update(self._create_cors_headers(request))
        return headers, json.dumps(token), 200


class DeviceCodeGrantEx(GrantTypeBase):
    def __init__(self, request_validator=None, **kwargs):
        # overwrite with custom proxy_target
        self.proxy_target = OAuth2DeviceCodeGrantEx(request_validator=request_validator, **kwargs)
        self.register_token_modifier(self.add_id_token)
