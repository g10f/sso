# -*- coding: utf-8 -*-
from sso.auth.backends import SSOBackend

class OAuth2Backend(SSOBackend):
    def authenticate(self, token=None, **kwargs):
        if token:
            return token.user
        
        return None
