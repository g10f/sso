import logging

from oauthlib.oauth2.rfc6749 import tokens
from oauthlib.oauth2.rfc6749.endpoints import AuthorizationEndpoint, RevocationEndpoint, TokenEndpoint
from oauthlib.oauth2.rfc6749.endpoints.introspect import IntrospectEndpoint
from oauthlib.oauth2.rfc6749.grant_types import ImplicitGrant as OAuth2ImplicitGrant, ClientCredentialsGrant, \
    ResourceOwnerPasswordCredentialsGrant
from oauthlib.openid.connect.core.grant_types import ImplicitGrant
from oauthlib.openid.connect.core.grant_types.dispatchers import AuthorizationCodeGrantDispatcher, \
    ImplicitTokenGrantDispatcher, AuthorizationTokenGrantDispatcher

from django.conf import settings
from .oidc_grants import OAuth2AuthorizationCodeGrantEx, AuthorizationCodeGrantEx, HybridGrantEx, RefreshTokenGrantEx
from .oidc_request_validator import OIDCRequestValidator
from .oidc_token import get_token_generator

logger = logging.getLogger(__name__)


# SUPPORTED_SCOPES = ['openid', 'profile', 'email', 'offline_access', 'address', 'phone']
# DEFAULT_SCOPES = ['openid', 'profile']


class Server(AuthorizationEndpoint, IntrospectEndpoint, TokenEndpoint, RevocationEndpoint):
    """ An all-in-one endpoint  see oauthlib.openid.connect.core.endpoints.pre_configured """

    def __init__(self, request_validator, token_expires_in=None, token_generator=None, refresh_token_generator=None,
                 *args, **kwargs):
        auth_grant_ex = OAuth2AuthorizationCodeGrantEx(request_validator)
        implicit_grant = OAuth2ImplicitGrant(request_validator)
        password_grant = ResourceOwnerPasswordCredentialsGrant(request_validator)
        credentials_grant = ClientCredentialsGrant(request_validator)
        refresh_grant = RefreshTokenGrantEx(request_validator)
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
oidc_server = Server(oidc_request_validator, token_expires_in=getattr(settings, 'SSO_ACCESS_TOKEN_AGE', 3600),
                     token_generator=get_token_generator(), refresh_token_generator=tokens.random_token_generator)
