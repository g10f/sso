from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AccountsConfig(AppConfig):
    name = 'sso.accounts'
    verbose_name = _("Accounts")

    def ready(self):
        # connect the receivers
        # https://docs.djangoproject.com/en/1.8/topics/signals/
        # noinspection PyUnresolvedReferences
        from . import signals
