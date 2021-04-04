from base64 import b32encode

from binascii import unhexlify

from django import forms
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from sso.auth.models import TOTPDevice, Profile, Device
from sso.auth.utils import get_qrcode_data_url, totp_digits
from sso.forms import bootstrap


class CredentialSetupForm(forms.Form):
    name = forms.CharField(max_length=255, required=False, widget=bootstrap.TextInput(), help_text="The human-readable name of this device.")


class AddU2FForm(CredentialSetupForm):
    u2f_response = forms.CharField(label=_('Response'), widget=forms.HiddenInput())
    u2f_request = forms.CharField(label=_('Request'), widget=forms.HiddenInput())


class ProfileForm(forms.Form):
    default = forms.IntegerField(required=False)
    delete = forms.IntegerField(required=False)
    is_otp_enabled = forms.NullBooleanField()

    def __init__(self, user, **kwargs):
        super().__init__(**kwargs)
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


class TOTPDeviceForm(CredentialSetupForm):
    token = forms.IntegerField(label=_("One-time code"), min_value=0, max_value=int('9' * totp_digits()),
                               widget=bootstrap.TextInput(attrs={'autofocus': True}))
    key = forms.CharField(label=_('Key'), widget=forms.HiddenInput())

    error_messages = {
        'invalid_token': _('Invalid token value: %(token)s.'),
    }

    def __init__(self, user, issuer, **kwargs):
        super().__init__(**kwargs)
        self.digits = totp_digits()
        self.user = user
        self.issuer = issuer
        self.device = None

    @property
    def qr_code(self):
        key = self.data.get('key', self.initial['key'])
        rawkey = unhexlify(key.encode('ascii'))
        b32key = b32encode(rawkey).decode('utf-8')
        return get_qrcode_data_url(b32key, force_str(self.user), self.issuer)

    def clean(self):
        cd = super().clean()
        if 'token' in cd:
            token = cd.get("token")
            defaults = {
                'key': cd['key'],
                'digits': self.digits,
                'tolerance': 2,
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
        self.device.name = self.data['name']
        self.device.save(update_fields=['confirmed', 'name'])
        if not hasattr(self.user, 'sso_auth_profile'):
            Profile.objects.create(user=self.user, default_device=self.device, is_otp_enabled=True)

        return self.device
