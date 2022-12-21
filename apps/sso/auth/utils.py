import base64
import logging
import time
from binascii import unhexlify, hexlify
from functools import lru_cache
from io import BytesIO
from os import urandom

import pyotp
import qrcode

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ValidationError
from django.shortcuts import resolve_url
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme
from sso.auth.apps import AuthConfig
from sso.utils.http import get_request_param
from sso.utils.url import get_base_url

logger = logging.getLogger(__name__)


def is_browser_client(request):
    return request.client and request.client.uuid == settings.SSO_BROWSER_CLIENT_ID


def is_recent_auth_time(request, max_age=None):
    """
    check if the cookie is recent
    if max_age is None and settings.SSO_ADMIN_MAX_AGE is also None
    then there is no checking
    """
    from sso.auth import SESSION_AUTH_DATE
    if SESSION_AUTH_DATE in request.session:
        max_age = max_age if max_age else settings.SSO_ADMIN_MAX_AGE
        if max_age is None:
            return True

        now = int(time.time())
        session_auth_date = request.session[SESSION_AUTH_DATE]
        return session_auth_date + int(max_age) >= now
    return True


@lru_cache()
def get_device_classes():
    from sso.auth.models import Device
    device_classes = []
    for model in Device.devices:
        device_class = django_apps.get_model(AuthConfig.label, model[0])
        device_classes.append(device_class)
    return device_classes


def get_device_classes_for_user(user):
    from sso.auth.models import Device
    device_classes = set()
    for device in Device.objects.filter(user=user, confirmed=True):
        device_class = device.get_child().__class__
        device_classes.add(device_class)
    return device_classes


def get_device_class_by_app_label(model_name):
    return django_apps.get_model(AuthConfig.label, model_name)


def should_use_mfa(user):
    return get_device_classes() and (not settings.SSO_ADMIN_ONLY_2F or user.is_user_admin or user.is_organisation_admin or user.is_staff)


def totp_digits():
    """
    Returns the number of digits (as configured by the TWO_FACTOR_TOTP_DIGITS setting)
    for totp tokens. Defaults to 6
    """
    return getattr(settings, 'TWO_FACTOR_TOTP_DIGITS', 6)


def match_token(user, token):
    """
    Attempts to verify a :term:`token` on every device attached to the given
    user until one of them succeeds. When possible, you should prefer to verify
    tokens against specific devices.
    """
    matches = (d for d in otp_devices_for_user(user) if d.verify_token(token))
    return next(matches, None)


def otp_devices_for_user(user, confirmed=True):
    from sso.auth.models import TOTPDevice
    if user.is_anonymous:
        return None
    return TOTPDevice.objects.filter(user=user, confirmed=confirmed)


def get_safe_login_redirect_url(request):
    from sso.oauth2.models import allowed_hosts

    redirect_to = get_request_param(request, REDIRECT_FIELD_NAME, '')
    # Ensure the user-originating redirection url is safe.
    # allow external hosts, for redirect after password_create_complete
    if url_has_allowed_host_and_scheme(redirect_to, allowed_hosts=allowed_hosts()):
        return redirect_to
    else:
        return resolve_url(settings.LOGIN_REDIRECT_URL)


def hex_validator(length=0):
    """
    Returns a function to be used as a model validator for a hex-encoded
    CharField. This is useful for secret keys of all kinds::

        def key_validator(value):
            return hex_validator(20)(value)

        key = models.CharField(max_length=40, validators=[key_validator], help_text=u'A hex-encoded 20-byte secret key')

    :param int length: If greater than 0, validation will fail unless the
        decoded value is exactly this number of bytes.

    :rtype: function

    >>> hex_validator()('0123456789abcdef')
    >>> hex_validator(8)(b'0123456789abcdef')
    >>> hex_validator()('phlebotinum')          # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValidationError: ['phlebotinum is not valid hex-encoded data.']
    >>> hex_validator(9)('0123456789abcdef')    # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValidationError: ['0123456789abcdef does not represent exactly 9 bytes.']
    """

    def _validator(value):
        try:
            if isinstance(value, str):
                value = value.encode()

            unhexlify(value)
        except Exception:
            raise ValidationError('{0} is not valid hex-encoded data.'.format(value))

        if (length > 0) and (len(value) != length * 2):
            raise ValidationError('{0} does not represent exactly {1} bytes.'.format(value, length))

    return _validator


def random_hex(length=20):
    """
    Returns a string of random bytes encoded as hex. This uses
    :func:`os.urandom`, so it should be suitable for generating cryptographic
    keys.

    :param int length: The number of (decoded) bytes to return.

    :returns: A string of hex digits.
    :rtype: str
    """
    return hexlify(urandom(length))


def get_qrcode_data_url(key, username, issuer):
    # Get data for qrcode
    from qrcode.image.pil import PilImage
    if settings.SSO_USE_HTTPS:
        base_uri = get_base_url()
        image = base_uri + static("root/apple-touch-icon.png")
    else:
        image = None

    otpauth_url = pyotp.TOTP(key, digits=totp_digits()).provisioning_uri(
        name=username, issuer_name=issuer, image=image)

    # Make and return QR code
    img = qrcode.make(otpauth_url, image_factory=PilImage, box_size=3)
    output = BytesIO()
    img.save(output)
    data = base64.b64encode(output.getvalue()).decode('ascii')
    return "data:image/png;base64,%s" % data
