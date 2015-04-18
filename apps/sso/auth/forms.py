# -*- coding: utf-8 -*-
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from django.utils.timezone import now
from sso.forms import bootstrap
from utils.translation import string_format


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        max_length=75,
        error_messages={'required': _('Please enter your Email address or Username.')}, 
        label=_("Email address or Username"), 
        widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('Email address or Username')), 'autofocus': ''}))
    password = forms.CharField(
        label=_("Password"), 
        error_messages={'required': _('Please enter your Password.')}, 
        widget=bootstrap.PasswordInput(attrs={'placeholder': capfirst(_('Password'))}))
    remember_me = forms.BooleanField(label=_('Remember me'),
                                     help_text=string_format(_('Stay logged in for %(days)d days'), {'days': timedelta(seconds=settings.SESSION_COOKIE_AGE).days}),
                                     required=False)
    error_messages = {
        'invalid_login': _("Please enter a correct %(username)s and password. "
                           "Note that both fields may be case-sensitive."),
        'inactive': _("This account is inactive."),
        'expired': _("This account has expired. Please contact the user administrator in your organisation %s."),
        'whitespaces': _("Please enter your Email address or Username without whitespaces at the beginning or end."),
    }

    def clean_username(self):
        # check if there are whitespaces at the beginning or end of the username
        data = self.cleaned_data['username']
        if data and data != data.strip():
            raise forms.ValidationError(self.error_messages['whitespaces'], code='whitespaces')
        return data

    def confirm_login_allowed(self, user):
        super(EmailAuthenticationForm, self).confirm_login_allowed(user)

        # check if the activation is not expired
        validate = False
        if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
            if settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
                validate = True
            else:
                for organisation in user.organisations.all().only('uses_user_activation', 'name'):
                    if organisation.uses_user_activation:
                        validate = True
                        break
        if validate:
            if user.valid_until is not None and user.valid_until < now():
                msg = ", ".join([o.name for o in user.organisations.all()])
                raise forms.ValidationError(
                    self.error_messages['expired'] % msg,
                    code='expired',
                )
