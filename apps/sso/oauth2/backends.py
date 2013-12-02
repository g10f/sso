# -*- coding: utf-8 -*-
from django.contrib.auth.backends import ModelBackend

class OAuth2Backend(ModelBackend):
    def authenticate(self, token=None, **kwargs):
        if token:
            return token.user
        
        return None
