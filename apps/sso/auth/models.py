import json
import logging

import time
from binascii import unhexlify
from u2flib_server import u2f

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from sso.auth.forms import AuthenticationTokenForm, U2FForm
from sso.auth.oath import TOTP
from sso.auth.utils import random_hex, hex_validator
from sso.models import AbstractBaseModel

logger = logging.getLogger(__name__)


class Device(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             help_text=_("The user that this device belongs to."))
    name = models.CharField(max_length=255, blank=True, help_text=_("The human-readable name of this device."))
    confirmed = models.BooleanField(default=False, help_text=_("Is this device ready for use?"))
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    last_used = models.DateTimeField(null=True, blank=True, help_text=_("Last time this device was used?"))
    order = models.IntegerField(default=0, help_text=_('Overwrites the alphabetic order.'))

    DEVICES = [cls.split('.')[-1].lower() for cls in settings.OTP_DEVICES]

    def __str__(self):
        return "%s" % self.get_child()

    class Meta:
        ordering = ['order', 'name']

    def get_child(self):
        for device in self.DEVICES:
            if hasattr(self, device):
                return getattr(self, device)

    def challenges(self):
        return self.get_child().challenges()

    @property
    def image(self):
        return self.get_child().image

    @property
    def login_form_class(self):
        return self.get_child().login_form_class

    @property
    def login_form_templates(self):
        return self.get_child().login_form_templates

    @property
    def login_text(self):
        return self.get_child().login_text

    def generate_challenge(self):
        return self.get_child().generate_challenge()

    def verify_token(self, token):
        return self.get_child().verify_token(token)


def default_key():
    return random_hex(20)


def key_validator(value):
    return hex_validator()(value)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sso_auth_profile')
    default_device = models.ForeignKey(Device, on_delete=models.CASCADE)
    is_otp_enabled = models.BooleanField(_('is otp enabled'), default=False)


class U2FDevice(Device):
    version = models.TextField(default="U2F_V2")
    public_key = models.TextField()
    key_handle = models.TextField()
    app_id = models.TextField()

    def to_json(self):
        return {
            'publicKey': self.public_key,
            'keyHandle': self.key_handle,
            'appId': self.app_id,
            "version": self.version
        }

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return "%s:%s" % (self.__class__.__name__, self.user_id)

    @classmethod
    def detail_template(cls):
        return 'auth/u2f/detail.html'

    def challenges(self):
        u2f_devices = U2FDevice.objects.filter(user=self.user, confirmed=True)
        devices = [d.to_json() for d in u2f_devices]
        sign_request = u2f.begin_authentication(self.app_id, devices)
        return json.dumps(sign_request)

    @property
    def image(self):
        return 'img/u2f_yubikey.png'

    @property
    def login_form_class(self):
        return U2FForm

    @property
    def login_form_templates(self):
        return 'auth/u2f/verify.html'

    @property
    def login_text(self):
        return _('Please touch the flashing %(name)s U2F device now. You may be prompted to allow the site permission to access your security keys. '
                 'After granting permission, the device will start to blink.') % {'name': self.name}

    @property
    def default_name(self):
        return _('U2F Device')

    def generate_challenge(self):
        pass

    def verify_token(self, token):
        pass


class TOTPDevice(Device):
    """
    A generic TOTP :class:`~sso.auth.models.Device`. The model fields mostly
    correspond to the arguments to :func:`sso.auth.oath.totp`. They all have
    sensible defaults, including the key, which is randomly generated.

    .. attribute:: key

        *CharField*: A hex-encoded secret key of up to 40 bytes. (Default: 20
        random bytes)


    .. attribute:: step

        *PositiveSmallIntegerField*: The time step in seconds. (Default: 30)

    .. attribute:: t0

        *BigIntegerField*: The Unix time at which to begin counting steps.
        (Default: 0)

    .. attribute:: digits

        *PositiveSmallIntegerField*: The number of digits to expect in a token
        (6 or 8).  (Default: 6)

    .. attribute:: tolerance

        *PositiveSmallIntegerField*: The number of time steps in the past or
        future to allow. For example, if this is 1, we'll accept any of three
        tokens: the current one, the previous one, and the next one. (Default:
        1)

    .. attribute:: drift

        *SmallIntegerField*: The number of time steps the prover is known to
        deviate from our clock.  If :setting:`OTP_TOTP_SYNC` is ``True``, we'll
        update this any time we match a token that is not the current one.
        (Default: 0)

    .. attribute:: last_t

        *BigIntegerField*: The time step of the last verified token. To avoid
        verifying the same token twice, this will be updated on each successful
        verification. Only tokens at a higher time step will be verified
        subsequently. (Default: -1)

    """
    key = models.CharField(max_length=80, validators=[key_validator], default=default_key,
                           help_text="A hex-encoded secret key of up to 40 bytes.")
    step = models.PositiveSmallIntegerField(default=30, help_text="The time step in seconds.")
    t0 = models.BigIntegerField(default=0, help_text="The Unix time at which to begin counting steps.")
    digits = models.PositiveSmallIntegerField(choices=[(6, 6), (8, 8)], default=6,
                                              help_text="The number of digits to expect in a token.")
    tolerance = models.PositiveSmallIntegerField(default=1,
                                                 help_text="The number of time steps in the past or future to allow.")
    drift = models.SmallIntegerField(default=0,
                                     help_text="The number of time steps the prover is known to deviate from our clock.")
    last_t = models.BigIntegerField(default=-1,
                                    help_text="The t value of the latest verified token. The next token must be at a higher time step.")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return "%s:%s" % (self.__class__.__name__, self.user_id)

    @classmethod
    def detail_template(cls):
        return 'auth/totp/detail.html'

    def challenges(self):
        return None

    @property
    def image(self):
        return 'img/totp.png'

    @property
    def login_form_class(self):
        return AuthenticationTokenForm

    @property
    def login_form_templates(self):
        return 'auth/totp/verify.html'

    @property
    def login_text(self):
        return _('Please enter the one-time code from your %(name)s authenticator.') % {'name': self.name}

    @property
    def default_name(self):
        return _('TOTP Authenticator')

    @property
    def bin_key(self):
        """
        The secret key as a binary string.
        """
        return unhexlify(self.key.encode())

    def generate_challenge(self):
        pass

    def verify_token(self, token):
        otp_totp_sync = getattr(settings, 'OTP_TOTP_SYNC', True)

        try:
            token = int(token)
        except Exception:
            verified = False
        else:
            key = self.bin_key

            totp = TOTP(key, self.step, self.t0, self.digits)
            totp.time = time.time()

            for offset in range(-self.tolerance, self.tolerance + 1):
                totp.drift = self.drift + offset
                if (totp.t() > self.last_t) and (totp.token() == token):
                    self.last_t = totp.t()
                    if (offset != 0) and otp_totp_sync:
                        self.drift += offset

                    self.last_used = timezone.now()
                    self.save()

                    verified = True
                    break
            else:
                verified = False

        return verified
