import base64
import StringIO
from binascii import unhexlify, hexlify
from os import urandom
from urllib import quote, urlencode

import qrcode

from django.core.exceptions import ValidationError
from django.utils import six
from django.conf import settings
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.decorators import method_decorator
from http.util import get_request_param


def totp_digits():
    """
    Returns the number of digits (as configured by the TWO_FACTOR_TOTP_DIGITS setting)
    for totp tokens. Defaults to 6
    """
    return getattr(settings, 'TWO_FACTOR_TOTP_DIGITS', 6)


def class_view_decorator(function_decorator):
    """
    Converts a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.

    From: http://stackoverflow.com/a/8429311/58107
    """
    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View
    return simple_decorator


def default_device(user, is_otp_enabled=True):
    from sso.auth.models import Device
    try:
        if is_otp_enabled is not None:
            return Device.objects.get(profile__user=user, profile__is_otp_enabled=is_otp_enabled, confirmed=True)
        else:
            return Device.objects.get(profile__user=user, confirmed=True)

    except Device.DoesNotExist:
        return None


def match_token(user, token):
    """
    Attempts to verify a :term:`token` on every device attached to the given
    user until one of them succeeds. When possible, you should prefer to verify
    tokens against specific devices.
    """
    matches = (d for d in devices_for_user(user) if d.verify_token(token))

    return next(matches, None)


def devices_for_user(user, confirmed=True):
    from sso.auth.models import Device
    if user.is_anonymous():
        return Device.objects.none()

    return Device.objects.filter(user=user, confirmed=confirmed)


def get_safe_login_redirect_url(request):
    redirect_to = get_request_param(request, REDIRECT_FIELD_NAME, '')
    # Ensure the user-originating redirection url is safe.
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        return resolve_url(settings.LOGIN_REDIRECT_URL)
    else:
        return redirect_to


def get_otpauth_url(accountname, secret, issuer=None, digits=None):
    # For a complete run-through of all the parameters, have a look at the
    # specs at:
    # https://code.google.com/p/google-authenticator/wiki/KeyUriFormat

    # quote and urlencode work best with bytes, not unicode strings.
    accountname = accountname.encode('utf8')
    issuer = issuer.encode('utf8') if issuer else None

    label = quote(b': '.join([issuer, accountname]) if issuer else accountname)

    query = {
        'secret': secret,
        'digits': digits or totp_digits()
    }

    if issuer:
        query['issuer'] = issuer

    return 'otpauth://totp/%s?%s' % (label, urlencode(query))



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
            if isinstance(value, six.text_type):
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
    otpauth_url = get_otpauth_url(accountname=username,
                                  issuer=issuer,
                                  secret=key,
                                  digits=totp_digits())

    # Make and return QR code
    img = qrcode.make(otpauth_url, image_factory=PilImage, box_size=3)
    output = StringIO.StringIO()
    img.save(output)
    return "data:image/png;base64,%s" % base64.b64encode(output.getvalue())