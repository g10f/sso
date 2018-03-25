import json
import logging
import time
from binascii import unhexlify

import requests
from u2flib_server import u2f

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from sso.auth.forms import AuthenticationTokenForm, U2FForm
from sso.auth.oath import TOTP
from sso.auth.utils import random_hex, hex_validator
from sso.models import AbstractBaseModel
from sso.utils.translation import string_format

logger = logging.getLogger(__name__)


class Device(AbstractBaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             help_text="The user that this device belongs to.")
    name = models.CharField(max_length=255, blank=True, help_text="The human-readable name of this device.")
    confirmed = models.BooleanField(default=False, help_text="Is this device ready for use?")
    created_at = models.DateTimeField(_('created at'), default=timezone.now)
    last_used = models.DateTimeField(null=True, blank=True, help_text="Last time this device was used?")
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
    def setup_template(cls):
        return 'auth/include/u2f_profile.html'

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
        return 'auth/u2f/verify_key.html'

    @property
    def login_text(self):
        return _('Please touch the flashing U2F device now. \
        You may be prompted to allow the site permission to access your security keys. After granting permission, the device will start to blink.')

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
    def setup_template(cls):
        return 'auth/include/totp_profile.html'

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
        return 'auth/token.html'

    @property
    def login_text(self):
        return _('Please enter the tokens generated by your token generator.')

    @property
    def default_name(self):
        return _('Authenticator App')

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


class TwilioSMSDevice(Device):
    """
    A :class:`~sso.auth.models.Device` that delivers codes via the Twilio SMS
    service. This uses TOTP to generate temporary tokens, which are valid for
    :setting:`OTP_TWILIO_TOKEN_VALIDITY` seconds. Once a given token has been
    accepted, it is no longer valid, nor is any other token generated at an
    earlier time.

    .. attribute:: number

        *CharField*: The mobile phone number to deliver to.

    .. attribute:: key

        *CharField*: The secret key used to generate TOTP tokens.

    .. attribute:: last_t

        *BigIntegerField*: The t value of the latest verified token.

    """
    number = models.CharField(max_length=16, help_text="The mobile number to deliver tokens to.")
    key = models.CharField(max_length=40, validators=[key_validator], default=default_key,
                           help_text="A random key used to generate tokens (hex-encoded).")
    last_t = models.BigIntegerField(default=-1,
                                    help_text="The t value of the latest verified token. The next token must be at a higher time step.")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return "%s:%s:%s" % (self.__class__.__name__, self.user_id, self.number)

    @classmethod
    def setup_template(cls):
        return 'auth/include/phone_profile.html'

    def challenges(self):
        return None

    @property
    def image(self):
        return 'img/sms.png'

    @property
    def login_form_class(self):
        return AuthenticationTokenForm

    @property
    def login_form_templates(self):
        return 'auth/token.html'

    @property
    def login_text(self):
        return _('We sent you a text message to %(number)s, please enter the token we sent.') % {'number': self.number}

    @property
    def default_name(self):
        return _('Phone %(number)s') % {'number': self.number}

    @property
    def bin_key(self):
        return unhexlify(self.key.encode())

    def generate_challenge(self):
        """
        Sends the current TOTP token to ``self.number``.
        :returns: :setting:`OTP_TWILIO_CHALLENGE_MESSAGE` on success.
        :raises: Exception if delivery fails.
        """
        totp = self.totp_obj()
        token = format(totp.token(), '06d')
        message = string_format(_('Your %(brand)s verification code is {token}'), {'brand': settings.SSO_BRAND}).format(
            token=token)

        if settings.OTP_TWILIO_NO_DELIVERY:
            logger.info(message)
        else:
            self._deliver_token(message)

        if settings.DEBUG:
            challenge = _("Sent code {code} by SMS to {number}").format(number=self.number, code=token)
        else:
            challenge = _("Sent code by SMS to {number}").format(number=self.number)

        return challenge

    def _deliver_token(self, token):
        self._validate_config()

        url = 'https://api.twilio.com/2010-04-01/Accounts/{0}/SMS/Messages.json'.format(settings.OTP_TWILIO_ACCOUNT)
        data = {
            'From': settings.OTP_TWILIO_FROM,
            'To': self.number,
            'Body': str(token),
        }

        response = requests.post(
            url, data=data,
            auth=(settings.OTP_TWILIO_ACCOUNT, settings.OTP_TWILIO_AUTH)
        )

        try:
            response.raise_for_status()
        except Exception as e:
            logger.exception('Error sending token by Twilio SMS: {0}'.format(e))
            raise

        if 'sid' not in response.json():
            message = response.json().get('message')
            logger.error('Error sending token by Twilio SMS: {0}'.format(message))
            raise Exception(message)

    def _validate_config(self):
        if settings.OTP_TWILIO_ACCOUNT is None:
            raise ImproperlyConfigured('OTP_TWILIO_ACCOUNT must be set to your Twilio account identifier')

        if settings.OTP_TWILIO_AUTH is None:
            raise ImproperlyConfigured('OTP_TWILIO_AUTH must be set to your Twilio auth token')

        if settings.OTP_TWILIO_FROM is None:
            raise ImproperlyConfigured('OTP_TWILIO_FROM must be set to one of your Twilio phone numbers')

    def verify_token(self, token):
        try:
            token = int(token)
        except Exception:
            verified = False
        else:
            totp = self.totp_obj()
            tolerance = settings.OTP_TWILIO_TOKEN_VALIDITY

            for offset in range(-tolerance, 1):
                totp.drift = offset
                if (totp.t() > self.last_t) and (totp.token() == token):
                    self.last_t = totp.t()
                    self.last_used = timezone.now()
                    self.save()

                    verified = True
                    break
            else:
                verified = False

        return verified

    def totp_obj(self):
        totp = TOTP(self.bin_key, step=1)
        totp.time = time.time()

        return totp
