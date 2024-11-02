import json
import logging
from base64 import b32encode

import pyotp
from binascii import unhexlify
from fido2 import cbor
from fido2.cose import CoseKey
from fido2.features import webauthn_json_mapping
from fido2.server import Fido2Server, U2FFido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import PublicKeyCredentialRpEntity, AttestedCredentialData, \
    PublicKeyCredentialUserEntity
from pyotp.utils import strings_equal

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.auth.forms import AuthenticationTokenForm, U2FForm
from sso.auth.utils import random_hex, hex_validator, get_device_class_by_app_label
from sso.models import AbstractBaseModel

logger = logging.getLogger(__name__)
webauthn_json_mapping.enabled = True


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

    if settings.SSO_WEBAUTHN_VERSION == "U2F_V2":
        u2f_app_id = f"{'https' if settings.SSO_USE_HTTPS else 'http'}://{settings.SSO_DOMAIN.lower().split(':')[0]}"
        fido2_server = U2FFido2Server(u2f_app_id, PublicKeyCredentialRpEntity(id=settings.SSO_DOMAIN.lower().split(':')[0],
                                                                              name=f'{settings.SSO_SITE_NAME}'))
    else:
        fido2_server = Fido2Server(PublicKeyCredentialRpEntity(name=settings.SSO_SITE_NAME, id=settings.SSO_DOMAIN.lower().split(':')[0]))
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
        user_entity = PublicKeyCredentialUserEntity(id=user.uuid.bytes, name=user.username, display_name=user.get_full_name())
        extensions = None
        user_verification = None
        authenticator_attachment = None
        if settings.SSO_WEBAUTHN_VERSION == "U2F_V2":
            # default for U2F_V2
            extensions = {}
        if settings.SSO_WEBAUTHN_EXTENSIONS:
            extensions = {"credProps": settings.SSO_WEBAUTHN_CREDPROPS}
        if settings.SSO_WEBAUTHN_USER_VERIFICATION:
            user_verification = settings.SSO_WEBAUTHN_USER_VERIFICATION
        if settings.SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT:
            authenticator_attachment = settings.SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT

        options, state = cls.fido2_server.register_begin(
            user=user_entity,
            credentials=credentials,
            extensions=extensions,
            user_verification=user_verification,
            authenticator_attachment=authenticator_attachment
        )
        u2f_request = {
            'req': dict(options),
            'state': signing.dumps(state, salt=user.uuid.hex)
        }
        return json.dumps(u2f_request)

    @classmethod
    def register_complete(cls, name, response_data, state_data, user):
        state = signing.loads(state_data, salt=user.uuid.hex)
        logger.debug(f"Response: {response_data}")
        response = json.loads(response_data)
        auth_data = cls.fido2_server.register_complete(state, response=response)
        logger.debug(auth_data)

        public_key = websafe_encode(cbor.encode(auth_data.credential_data.public_key))
        aaguid = websafe_encode(auth_data.credential_data.aaguid)
        credential_id = websafe_encode(auth_data.credential_data.credential_id)

        device = U2FDevice.objects.create(name=name, user=user, public_key=public_key, credential_id=credential_id,
                                          aaguid=aaguid, confirmed=True, version=settings.SSO_WEBAUTHN_VERSION)
        return device

    @classmethod
    def authenticate_complete(cls, response_data, state_data, user):
        response = json.loads(response_data)
        state = signing.loads(state_data, salt=user.uuid.hex)
        credentials = U2FDevice.credentials(user)
        cred = cls.fido2_server.authenticate_complete(state=state, credentials=credentials, response=response)
        credential_id = websafe_encode(cred.credential_id)
        device = U2FDevice.objects.get(user=user, credential_id=credential_id)
        device.last_used = timezone.now()
        device.counter += 1
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
        user_verification = None
        if settings.SSO_WEBAUTHN_USER_VERIFICATION:
            user_verification = settings.SSO_WEBAUTHN_USER_VERIFICATION
        req, state = cls.fido2_server.authenticate_begin(credentials=credentials, user_verification=user_verification)
        sign_request = {
            'req': dict(req),
            'state': signing.dumps(state, salt=user.uuid.hex)
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
        return _('Please press the button below. You may be prompted to allow the site permission '
                 'to access your security key.')

    @classmethod
    def default_name(cls):
        return _('Security Key')


class TOTPDevice(Device):
    key = models.CharField(max_length=80, validators=[key_validator], default=default_key,
                           help_text="A hex-encoded secret key of up to 40 bytes.")
    step = models.PositiveSmallIntegerField(default=30, help_text="The time step in seconds.")
    digits = models.PositiveSmallIntegerField(choices=[(6, 6), (8, 8)], default=6,
                                              help_text="The number of digits to expect in a token.")
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
        return _('Authenticator App')

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

            valid_window = settings.SSO_TOTP_TOLERANCE
            for i in range(-valid_window, valid_window + 1):
                if strings_equal(str(token), str(totp.at(for_time, i))):
                    if self.last_t >= timecode + i:
                        # new last_t must be greate then the last
                        logger.warning(f'timecode {timecode + i} already used for device {self.uuid} from user {self.user}')
                        raise ValidationError(_("The Token was already used."))
                    else:
                        verified = True
                        self.last_t = timecode + i
                        self.last_used = for_time
                        self.save()
                    break
            else:
                logger.warning(f"TOTP verify failed. user: {self.user}, device {self.uuid}, token: {token}, for_time: {for_time}, valid_window: {valid_window}")
                verified = False

        return verified
