from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class OAuth2Config(AppConfig):
    name = 'sso.oauth2'
    verbose_name = _("OAuth2")
