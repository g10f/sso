# -*- coding: utf-8 -*-
import logging

from sso.auth.backends import SSOBackend

logger = logging.getLogger(__name__)


class OAuth2Backend(SSOBackend):
    def authenticate(self, request, token=None, **kwargs):
        if token:
            user = token.user
            try:
                # TODO: add otp_device to refresh token
                user.otp_device = token.otp_device
            except Exception as e:
                logger.warning(e)
            return user

        return None
