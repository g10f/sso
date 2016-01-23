# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = 'sso.auth'
    verbose_name = _("SSO Auth")
    label = 'sso_auth'
