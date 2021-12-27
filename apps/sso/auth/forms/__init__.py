import logging
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from sso.auth.utils import totp_digits, match_token
from sso.forms import bootstrap
from sso.utils.translation import string_format

logger = logging.getLogger(__name__)


class EmailAuthenticationForm(AuthenticationForm):
    labels = {
        'username': capfirst(_("Email address or Username")),
        'password': capfirst(_("Password"))
    }
    username = forms.CharField(
        max_length=75,
        error_messages={'required': _('Please enter your Email address or Username.')},
        label=labels.get('username'),
        widget=bootstrap.TextInput(attrs={
            'placeholder': labels.get('username'),
            'autofocus': True,
            'autocapitalize': 'none',
            'class': 'form-control-lg',
            'autocomplete': 'username'}))
    password = forms.CharField(
        label=labels.get('password'),
        error_messages={'required': _('Please enter your Password.')},
        widget=bootstrap.PasswordInput(attrs={
            'placeholder': labels.get('password'),
            'class': 'form-control-lg',
            'autocomplete': 'current-password'
        }))
    remember_me = forms.BooleanField(label=_('Remember me'),
                                     help_text=string_format(_('Stay logged in for %(days)d days'),
                                                             {'days': timedelta(seconds=settings.SESSION_COOKIE_AGE).days}),
                                     required=False,
                                     widget=bootstrap.CheckboxInput())
    error_messages = {
        'invalid_login': _("Please enter a correct %(username)s and password. Note that both fields may be case-sensitive."),
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


class U2FForm(forms.Form):
    response = forms.CharField(label=_('Response'), widget=forms.HiddenInput())
    challenges = forms.CharField(label=_('Challenges'), widget=forms.HiddenInput())
    state = forms.CharField(label=_('State'), widget=forms.HiddenInput())

    def __init__(self, device=None, **kwargs):
        self.user = kwargs.pop('user')
        self.device = device
        super().__init__(**kwargs)

    def clean(self):
        try:
            from sso.auth.models import U2FDevice
            U2FDevice.authenticate_complete(self.cleaned_data.get('response'), self.cleaned_data.get('state'), self.user)
        except Exception as e:
            raise forms.ValidationError(e)

        return self.cleaned_data


class AuthenticationTokenForm(forms.Form):
    labels = {
        'otp_token': capfirst(_("one-time password")),
    }
    otp_token = forms.IntegerField(label=labels.get('otp_token'),
                                   min_value=1, max_value=int('9' * totp_digits()),
                                   widget=bootstrap.TextInput(attrs={
                                       'placeholder': labels.get('otp_token'),
                                       'autofocus': True,
                                       'autocomplete': 'one-time-code',
                                       'class': 'form-control-lg'
                                   }))

    def __init__(self, device=None, **kwargs):
        self.user = kwargs.pop('user')
        self.device = device
        super().__init__(**kwargs)

    def clean(self):
        if self.user is None:
            raise forms.ValidationError(_('User is none'))

        token = self.cleaned_data.get('otp_token')
        device = self._verify_token(token)
        if device is None:
            raise forms.ValidationError(_('One-time code does not match.'))

        return self.cleaned_data

    def _verify_token(self, token):
        if self.device is not None:
            device = self.device if self.device.verify_token(token) else None
        else:
            device = match_token(self.user, token)

        return device
