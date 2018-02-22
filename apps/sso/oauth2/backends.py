import logging

from sso.auth.backends import SSOBackend

logger = logging.getLogger(__name__)


class OAuth2Backend(SSOBackend):
    def authenticate(self, request, token=None, **kwargs):
        if token:
            user = token.user
            try:
                # TODO: add otp_device to refresh token
                if hasattr(token, 'otp_device'):
                    user.otp_device = token.otp_device
            except Exception as e:
                logger.error(e)
            return user

        return None
