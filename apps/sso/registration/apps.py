from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class RegistrationConfig(AppConfig):
    name = 'sso.registration'
    verbose_name = _("Registration")
