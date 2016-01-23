from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class EmailsConfig(AppConfig):
    name = 'sso.emails'
    verbose_name = _("Emails")
