from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthConfig(AppConfig):
    name = 'sso.auth'
    verbose_name = _("SSO Auth")
    label = 'sso_auth'
