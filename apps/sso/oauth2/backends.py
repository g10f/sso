# -*- coding: utf-8 -*-
from sso.auth.backends import SSOBackend


class OAuth2Backend(SSOBackend):
    def authenticate(self, token=None, **kwargs):
        if token:
            user = token.user
            user.otp_device = token.otp_device
            return user
        
        return None
