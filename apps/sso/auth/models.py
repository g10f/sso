import json
import logging
from base64 import b64encode, b64decode, b32encode
from binascii import unhexlify

import pyotp
from fido2 import cbor
from fido2.client import ClientData
from fido2.cose import CoseKey
from fido2.ctap2 import AttestedCredentialData, AuthenticatorData, AttestationObject
from fido2.server import U2FFido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import PublicKeyCredentialRpEntity, UserVerificationRequirement
from sorl.thumbnail import get_thumbnail

from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.auth.forms import AuthenticationTokenForm, U2FForm
from sso.auth.utils import random_hex, hex_validator, get_device_class_by_app_label
from sso.models import AbstractBaseModel
from sso.utils.url import absolute_url

logger = logging.getLogger(__name__)


class Device(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             help_text=_("The user that this device belongs to."))
    name = models.CharField(max_length=255, blank=True, help_text=_("The human-readable name of this device."))
    confirmed = models.BooleanField(default=False, help_text=_("Is this device ready for use?"))
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    last_used = models.DateTimeField(null=True, blank=True, help_text=_("Last time this device was used?"))
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))

    devices = set()

    def __str__(self):
        return "%s" % self.get_child()

    class Meta:
        ordering = ['order', 'name']

    def get_child(self):
        for device in self.devices:
            device = device[0].lower()
            if hasattr(self, device):
                return getattr(self, device)

    @classmethod
    def get_subclass(cls, device_id):
        model_name = next(filter(lambda d: d[1] == device_id, cls.devices))[0]
        return get_device_class_by_app_label(model_name)


def default_key():
    return random_hex(20)


def key_validator(value):
    return hex_validator()(value)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sso_auth_profile')
    is_otp_enabled = models.BooleanField(_('is otp enabled'), default=False)
    default_device_id = models.IntegerField(choices=Device.devices, default=None, null=True)


class U2FDevice(Device):
    version = models.TextField(default="U2F_V2")
    public_key = models.TextField()
    credential_id = models.TextField()
    aaguid = models.TextField()
    counter = models.IntegerField(default=0)

    # server = Fido2Server(PublicKeyCredentialRpEntity(settings.SSO_DOMAIN.lower().split(':')[0],
    # f'{settings.SSO_SITE_NAME} Server'))
    u2f_app_id = f"{'https' if settings.SSO_USE_HTTPS else 'http'}://{settings.SSO_DOMAIN.lower().split(':')[0]}"
    server = U2FFido2Server(u2f_app_id, PublicKeyCredentialRpEntity(settings.SSO_DOMAIN.lower().split(':')[0],
                                                                    f'{settings.SSO_SITE_NAME} Server'))
    WEB_AUTHN_SALT = 'sso.auth.models.U2FDevice'
    device_id = 1
    Device.devices.add((__qualname__, device_id))

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return "%s:%s:%s" % (self.__class__.__name__, self.user_id, self.pk)

    @classmethod
    def get_device_id(cls):
        return cls.device_id

    @classmethod
    def detail_template(cls):
        return 'sso_auth/u2f/detail.html'

    @classmethod
    def register_begin(cls, request):
        user = request.user
        credentials = U2FDevice.credentials(user)
        icon = absolute_url(request, get_thumbnail(user.picture, "60x60", crop="center").url) if user.picture else None
        registration_data, state = cls.server.register_begin(
            {
                "id": user.uuid.bytes,
                "name": user.username,
                "displayName": user.get_full_name(),
                "icon": icon
            },
            credentials,
            user_verification="discouraged"
        )
        u2f_request = {
            'req': b64encode(cbor.encode(registration_data)).decode(),
            'state': signing.dumps(state, salt=U2FDevice.WEB_AUTHN_SALT)
        }
        return u2f_request

    @classmethod
    def register_complete(cls, name, response_data, state_data, user):
        data = cbor.decode(b64decode(response_data))
        state = signing.loads(state_data, salt=U2FDevice.WEB_AUTHN_SALT)
        client_data = ClientData(data["clientDataJSON"])
        att_obj = AttestationObject(data["attestationObject"])
        logger.debug("clientData", client_data)
        logger.debug("AttestationObject:", att_obj)

        auth_data = cls.server.register_complete(state, client_data, att_obj)
        logger.debug(auth_data)
        public_key = websafe_encode(cbor.encode(auth_data.credential_data.public_key))
        aaguid = websafe_encode(auth_data.credential_data.aaguid)
        credential_id = websafe_encode(auth_data.credential_data.credential_id)

        device = U2FDevice.objects.create(name=name, user=user, public_key=public_key, credential_id=credential_id,
                                          aaguid=aaguid, confirmed=True, version="fido2")
        return device

    @classmethod
    def authenticate_complete(cls, response_data, state_data, user):
        response = cbor.decode(b64decode(response_data))
        state = signing.loads(state_data, salt=U2FDevice.WEB_AUTHN_SALT)
        credential_id = response["credentialId"]
        client_data = ClientData(response["clientDataJSON"])
        auth_data = AuthenticatorData(response["authenticatorData"])
        signature = response["signature"]

        credentials = U2FDevice.credentials(user)
        cred = cls.server.authenticate_complete(
            state,
            credentials,
            credential_id,
            client_data,
            auth_data,
            signature,
        )
        credential_id = websafe_encode(cred.credential_id)
        device = U2FDevice.objects.get(user=user, credential_id=credential_id)
        if auth_data.counter <= device.counter:
            # verify counter is increasing
            raise ValueError(f"login counter is not increasing. {auth_data.counter} <= {device.counter} ")
        device.last_used = timezone.now()
        device.counter = auth_data.counter
        device.save(update_fields=["last_used", "counter"])
        return device

    @classmethod
    def credentials(cls, user):
        u2f_devices = cls.objects.filter(user=user, confirmed=True)
        return [
            AttestedCredentialData.create(aaguid=websafe_decode(d.aaguid),
                                          credential_id=websafe_decode(d.credential_id),
                                          public_key=CoseKey.parse(cbor.decode(websafe_decode(d.public_key))))
            for d in u2f_devices
        ]

    @classmethod
    def challenges(cls, user):
        credentials = U2FDevice.credentials(user)
        req, state = cls.server.authenticate_begin(credentials=credentials,
                                                   user_verification=UserVerificationRequirement.DISCOURAGED)
        sign_request = {
            'req': b64encode(cbor.encode(req)).decode(),
            'state': signing.dumps(state, salt=cls.WEB_AUTHN_SALT)
        }
        return json.dumps(sign_request)

    @classmethod
    def image(cls):
        return 'img/u2f_yubikey.png'

    @classmethod
    def login_form_class(cls):
        return U2FForm

    @classmethod
    def login_form_templates(cls):
        return 'sso_auth/u2f/verify.html'

    @classmethod
    def login_text(cls):
        return _(
            'Please touch the flashing U2F device now. You may be prompted to allow the site permission '
            'to access your security keys. After granting permission, the device will start to blink.')

    @classmethod
    def default_name(cls):
        return _('FIDO2 or U2F Device')


class TOTPDevice(Device):
    key = models.CharField(max_length=80, validators=[key_validator], default=default_key,
                           help_text="A hex-encoded secret key of up to 40 bytes.")
    step = models.PositiveSmallIntegerField(default=30, help_text="The time step in seconds.")
    digits = models.PositiveSmallIntegerField(choices=[(6, 6), (8, 8)], default=6,
                                              help_text="The number of digits to expect in a token.")
    tolerance = models.PositiveSmallIntegerField(default=1,
                                                 help_text="The number of time steps in the past or future to allow.")
    last_t = models.BigIntegerField(
        default=-1,
        help_text="The t value of the latest verified token. The next token must be at a higher time step.")

    device_id = 2
    Device.devices.add((__qualname__, device_id))

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return "%s:%s:%s" % (self.__class__.__name__, self.user_id, self.pk)

    @classmethod
    def get_device_id(cls):
        return cls.device_id

    @classmethod
    def detail_template(cls):
        return 'sso_auth/totp/detail.html'

    @classmethod
    def challenges(cls, user):
        return None

    @classmethod
    def image(cls):
        return 'img/totp.png'

    @classmethod
    def login_form_class(cls):
        return AuthenticationTokenForm

    @classmethod
    def login_form_templates(cls):
        return 'sso_auth/totp/verify.html'

    @classmethod
    def login_text(cls):
        return _('Please enter the one-time code from your authenticator app.')

    @classmethod
    def default_name(cls):
        return _('TOTP Authenticator')

    @property
    def bin_key(self):
        """
        The secret key as a binary string.
        """
        return unhexlify(self.key.encode())

    def verify_token(self, token):
        try:
            token = int(token)
        except RuntimeError:
            verified = False
        else:
            b32key = b32encode(self.bin_key).decode()
            totp = pyotp.TOTP(b32key, interval=self.step, digits=self.digits)
            for_time = now()
            timecode = totp.timecode(for_time)

            valid_window = self.tolerance
            for i in range(-valid_window, valid_window + 1):
                if constant_time_compare(str(token), str(totp.at(for_time, i))):
                    if self.last_t >= timecode + i:
                        # new last_t must be greate then the last
                        logger.warning(f'timecode {timecode + i} already used for device {self.uuid} from '
                                       f'user {self.user}')
                        verified = False
                    else:
                        verified = True
                        self.last_t = timecode + i
                        self.last_used = for_time
                        self.save()
                    break
            else:
                verified = False

        return verified
