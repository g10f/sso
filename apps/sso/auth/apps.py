# -*- coding: utf-8 -*-
try:
    from django.apps import AppConfig
    
    class AuthConfig(AppConfig):
        name = 'sso.auth'
        verbose_name = "SSO Auth"
        label = 'sso_auth'

except ImportError:
    pass
