from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FormsConfig(AppConfig):
    name = 'sso.forms'
    verbose_name = _("Forms")
    label = 'sso_forms'
