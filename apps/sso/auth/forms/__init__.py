# -*- coding: utf-8 -*-
from datetime import timedelta
import json
from u2flib_server import u2f_v2
from django.utils import timezone
from django.utils.timezone import now

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst

from sso.auth.utils import totp_digits, match_token
from sso.forms import bootstrap
from sso.utils.translation import string_format


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

    """
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
    """


class U2FForm(forms.Form):
    response = forms.CharField(label=_('Response'), widget=forms.HiddenInput())
    challenges = forms.CharField(label=_('Challenges'), widget=forms.HiddenInput())

    def __init__(self, device=None, **kwargs):
        self.user = kwargs.pop('user')
        self.device = device
        super(U2FForm, self).__init__(**kwargs)

    def clean(self):
        try:
            from sso.auth.models import U2FDevice
            response = json.loads(self.cleaned_data.get('response'))
            challenges = json.loads(self.cleaned_data.get('challenges'))
            # find the right challenge, the based on the key the user inserted
            challenge = [c for c in challenges if c['keyHandle'] == response['keyHandle']][0]
            device = U2FDevice.objects.get(user=self.user, key_handle=response['keyHandle'])
            login_counter, touch_asserted = u2f_v2.verify_authenticate(
                device.to_json(),
                challenge,
                response,
            )
            # TODO: store login_counter and verify it's increasing
            device.last_used = timezone.now()
            device.save(update_fields=["last_used"])
        except Exception as e:
            raise forms.ValidationError(force_text(e))

        return self.cleaned_data


class AuthenticationTokenForm(forms.Form):
    otp_token = forms.IntegerField(label=_("Token"), min_value=1, max_value=int('9' * totp_digits()),
                                   widget=bootstrap.TextInput(attrs={'autofocus': ''}))

    def __init__(self, device=None, **kwargs):
        self.user = kwargs.pop('user')
        self.device = device
        super(AuthenticationTokenForm, self).__init__(**kwargs)

    def clean(self):
        if self.user is None:
            raise forms.ValidationError(_('User is none'))

        token = self.cleaned_data.get('otp_token')
        device = self._verify_token(token)
        if device is None:
            raise forms.ValidationError(_('token don\'t match'))

        return self.cleaned_data

    def _verify_token(self, token):
        if self.device is not None:
            device = self.device if self.device.verify_token(token) else None
        else:
            device = match_token(self.user, token)

        return device
