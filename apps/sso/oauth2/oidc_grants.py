import json
import logging

from oauthlib.oauth2 import InvalidRequestError
from oauthlib.oauth2 import RefreshTokenGrant as OAuth2RefreshTokenGrant
from oauthlib.oauth2.rfc6749 import errors
from oauthlib.oauth2.rfc6749.grant_types import AuthorizationCodeGrant as OAuth2AuthorizationCodeGrant
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
        # custom exrefresh_tokentension of original oauthlib
        # if request.client and request.client.type not in CONFIDENTIAL_CLIENTS and 'HTTP_ORIGIN' in request.headers:
        #     origin = request.headers['HTTP_ORIGIN']
        #     add_cors_header(origin, request.client, headers)
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
