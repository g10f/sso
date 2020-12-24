from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    name = 'sso.accounts'
    verbose_name = _("Accounts")

    def ready(self):
        from django.contrib.auth.models import update_last_login
        # disconnect the buildin function "update_last_login", because we have our own and don't
        # want to send a post save message, which causes a
        user_logged_in.disconnect(update_last_login, dispatch_uid='update_last_login')

        # connect the receivers
        # https://docs.djangoproject.com/en/1.8/topics/signals/
        # noinspection PyUnresolvedReferences
        from . import signals
