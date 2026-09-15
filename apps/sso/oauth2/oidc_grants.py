import json
import logging

from oauthlib.oauth2 import InvalidRequestError
from oauthlib.oauth2 import RefreshTokenGrant as OAuth2RefreshTokenGrant
from oauthlib.oauth2.rfc6749 import errors
from oauthlib.oauth2.rfc6749.grant_types import AuthorizationCodeGrant as OAuth2AuthorizationCodeGrant
from oauthlib.oauth2.rfc8628.grant_types.device_code import DeviceCodeGrant as OAuth2DeviceCodeGrant
from oauthlib.openid import RequestValidator
from oauthlib.openid.connect.core.grant_types import GrantTypeBase

logger = logging.getLogger(__name__)


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


class DeviceCodeGrantEx(GrantTypeBase):
    """
    RFC 8628 Device Authorization Grant, for clients with no keyboard (TVs) or no
    browser to redirect through (CLIs) -- same category of "public client" the
    existing 'native' Client type already covers for the out-of-band authorization
    code flow (see oauth2/views.py:approval).

    oauthlib ships the wire format (DeviceAuthorizationEndpoint, see oidc_server.py)
    and this proxy_target grant class, but its stock create_token_response():
      (a) unconditionally calls request_validator.authenticate_client(), which
          requires a client secret -- wrong here, since this grant exists
          specifically for clients that cannot hold one; and
      (b) implements none of the RFC 8628 polling semantics (authorization_pending /
          slow_down / expired_token / access_denied) or the pending -> approved
          handoff from the verification page.
    We reimplement create_token_response to add both, delegating the actual
    DeviceCode lookup/state machine to OIDCRequestValidator.validate_device_code().
    """
    def __init__(self, request_validator=None, **kwargs):
        # overwrite with custom proxy_target, matching the other Ex grants in this module
        self.proxy_target = OAuth2DeviceCodeGrant(request_validator=request_validator, **kwargs)

    def create_authorization_response(self, request, token_handler):
        raise NotImplementedError('Device code grant does not implement an authorization response')

    def create_token_response(self, request, token_handler):
        headers = self._get_default_headers()
        try:
            # Section 3.4 of RFC 8628: device_code requests come from public clients,
            # so we confirm client_id the same way AuthorizationCodeGrantEx does for
            # 'native' clients, not via authenticate_client()'s client_secret check.
            if not self.request_validator.authenticate_client_id(request.client_id, request):
                raise errors.InvalidClientError(request=request)

            device_code = self.request_validator.validate_device_code(
                request.client_id, request.device_code, request)
        except errors.OAuth2Error as e:
            logger.debug('Client error during device_code token request: %r.', e)
            headers.update(e.headers)
            return headers, e.json, e.status_code

        request.user = device_code.user
        request.scopes = device_code.scopes.split()
        request.client = device_code.client

        token = token_handler.create_token(request, refresh_token='offline_access' in request.scopes)
        for modifier in self._token_modifiers:
            token = modifier(token, token_handler, request)
        self.request_validator.save_token(token, request)
        self.request_validator.invalidate_device_code(device_code, request)

        headers.update(self._create_cors_headers(request))
        return headers, json.dumps(token), 200
