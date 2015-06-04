# -*- coding: utf-8 -*-
from base64 import b32encode
from binascii import unhexlify

from django.core.validators import RegexValidator
from django import forms
from django.utils.translation import ugettext_lazy as _

from sso.auth.utils import get_qrcode_data_url, totp_digits
from sso.auth.models import TwilioSMSDevice, TOTPDevice, Profile, Device
from sso.forms import bootstrap


class ProfileForm(forms.Form):
    default = forms.IntegerField(required=False)
    delete = forms.IntegerField(required=False)
    is_otp_enabled = forms.NullBooleanField()

    def __init__(self, user, **kwargs):
        super(ProfileForm, self).__init__(**kwargs)
        self.user = user

    def save(self):
        default = self.cleaned_data.get('default')
        delete = self.cleaned_data.get('delete')
        is_otp_enabled = self.cleaned_data.get('is_otp_enabled')

        if is_otp_enabled is not None:
            if is_otp_enabled:
                if Profile.objects.filter(user=self.user).exists():
                    Profile.objects.filter(user=self.user).update(is_otp_enabled=True)
                else:
                    device = Device.objects.filter(user=self.user).first()
                    if device:
                        Profile.objects.create(user=self.user, default_device=device, is_otp_enabled=True)
            else:
                Profile.objects.filter(user=self.user).update(is_otp_enabled=False)

        if default is not None:
            if not hasattr(self.user, 'sso_auth_profile'):
                Profile.objects.create(user=self.user, default_device_id=default)
            else:
                Profile.objects.filter(user=self.user).update(default_device_id=default)

        if delete is not None:
            Device.objects.filter(user=self.user, id=delete).delete()


phone_number_validator = RegexValidator(
    code='invalid-phone-number',
    regex='^(\+|00)',
    message=_('Please enter a valid phone number, including your country code '
              'starting with + or 00.'),
)


class AddPhoneForm(forms.Form):
    number = forms.CharField(label=_('Phone number'), validators=[phone_number_validator],
                             widget=bootstrap.TextInput(attrs={'autofocus': ''}))
    key = forms.CharField(label=_('Key'), widget=forms.HiddenInput())

    def __init__(self, user, **kwargs):
        super(AddPhoneForm, self).__init__(**kwargs)
        self.user = user

    def save(self):
        cd = self.cleaned_data
        sms_device, created = TwilioSMSDevice.objects.get_or_create(user=self.user, number=cd['number'], defaults={'key': cd['key']})
        if not created:
            sms_device.key = cd['key']

        sms_device.save()
        return sms_device


class AddU2FForm(forms.Form):
    response = forms.CharField(label=_('Response'), widget=bootstrap.Textarea())
    challenge = forms.CharField(label=_('Challenge'), required=False, widget=bootstrap.Textarea())


class PhoneSetupForm(forms.Form):
    token = forms.IntegerField(label=_("Token"), min_value=0, max_value=int('9' * totp_digits()),
                               widget=bootstrap.TextInput(attrs={'autofocus': ''}))

    error_messages = {
        'invalid_token': _('Invalid token value: %(token)s.'),
    }

    def __init__(self, sms_device, **kwargs):
        super(PhoneSetupForm, self).__init__(**kwargs)
        self.sms_device = sms_device

    def clean_token(self):
        token = self.cleaned_data['token']
        if not self.sms_device.verify_token(token):
            raise forms.ValidationError(self.error_messages['invalid_token'], params={'token': token})
        return token

    def save(self):
        self.sms_device.confirmed = True
        self.sms_device.save(update_fields=['confirmed'])

        return self.sms_device


class TOTPDeviceForm(forms.Form):
    token = forms.IntegerField(label=_("Token"), min_value=0, max_value=int('9' * totp_digits()),
                               widget=bootstrap.TextInput(attrs={'autofocus': ''}))
    key = forms.CharField(label=_('Key'), widget=forms.HiddenInput())

    error_messages = {
        'invalid_token': _('Invalid token value: %(token)s.'),
    }

    def __init__(self, user, issuer, **kwargs):
        super(TOTPDeviceForm, self).__init__(**kwargs)
        self.digits = totp_digits()
        self.user = user
        self.issuer = issuer
        self.device = None

    @property
    def qr_code(self):
        key = self.data.get('key', self.initial['key'])
        rawkey = unhexlify(key.encode('ascii'))
        b32key = b32encode(rawkey).decode('utf-8')
        return get_qrcode_data_url(b32key, str(self.user), self.issuer)

    def clean(self):
        cd = super(TOTPDeviceForm, self).clean()
        token = cd.get("token")
        defaults = {
            'key': cd['key'],
            'digits': self.digits
        }

        totp_device, created = TOTPDevice.objects.get_or_create(user=self.user, defaults=defaults)
        if not created:
            totp_device.key = cd['key']
            totp_device.last_t = -1  # reset value of the latest verified token

        self.device = totp_device

        if not self.device.verify_token(token):  # does an database update
            raise forms.ValidationError(self.error_messages['invalid_token'], params={'token': token})

    def save(self):
        self.device.confirmed = True
        self.device.save(update_fields=['confirmed'])
        if not hasattr(self.user, 'sso_auth_profile'):
            Profile.objects.create(user=self.user, default_device=self.device, is_otp_enabled=True)

        return self.device
