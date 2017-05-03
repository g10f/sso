from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class OrganisationsConfig(AppConfig):
    name = 'sso.organisations'
    verbose_name = _("Organisations")

    def ready(self):
        # connect the receivers
        # https://docs.djangoproject.com/en/1.8/topics/signals/
        from . import signals
