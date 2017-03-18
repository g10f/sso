import logging

from django.utils.deprecation import MiddlewareMixin

from .models import Device
from sso.auth import DEVICE_KEY

logger = logging.getLogger(__name__)


class IsVerified(object):
    """ A pickle-friendly lambda. """
    def __init__(self, user):
        self.user = user

    def __call__(self):
        return self.user.otp_device is not None

"""
Open ID Values:

http://openid.net/specs/openid-provider-authentication-policy-extension-1_0.html

http://schemas.openid.net/pape/policies/2007/06/phishing-resistant
http://schemas.openid.net/pape/policies/2007/06/multi-factor
http://schemas.openid.net/pape/policies/2007/06/multi-factor-physical
"""


class OTPMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    performs an analagous function. Just as AuthenticationMiddleware populates
    ``request.user`` based on session data, OTPMiddleware populates
    ``request.user.otp_device`` to the :class:`~sso.auth.models.Device`
    object that has verified the user, or ``None`` if the user has not been
    verified.  As a convenience, this also installs ``user.is_verified()``,
    which returns ``True`` if ``user.otp_device`` is not ``None``.
    """
    # TODO: include logic in oauth2 middleware and handle api case where there is no cookie only an access_token
    def process_request(self, request):
        user = getattr(request, 'user', None)

        if user is None:
            return None

        user.otp_device = None

        if user.is_anonymous():
            return None

        device_id = request.session.get(DEVICE_KEY)
        try:
            device = Device.objects.get(id=device_id) if device_id else None
        except Device.DoesNotExist:
            device = None
            del request.session[DEVICE_KEY]
            logger.warning('Device with id %d from session does not exist', device_id)

        if (device is not None) and (device.user_id != user.id):
            device = None

        if (device is None) and (DEVICE_KEY in request.session):
            del request.session[DEVICE_KEY]

        user.otp_device = device

        return None
