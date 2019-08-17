import logging
import time
import uuid

from django.conf import settings
from django.contrib.auth import rotate_token, user_logged_in, load_backend, BACKEND_SESSION_KEY, _get_backends
from django.utils.crypto import constant_time_compare, salted_hmac

logger = logging.getLogger(__name__)

default_app_config = 'sso.auth.apps.AuthConfig'

SESSION_AUTH_DATE = 'iat'
DEVICE_KEY = 'dev'
SESSION_KEY = 'sub'
HASH_SESSION_KEY = 'au_hash'  # shorter version of django _auth_user_hash


def _get_user_session_key(request):
    try:
        return uuid.UUID(request.session[SESSION_KEY]).hex
    except ValueError:
        pass

    return None


def _get_user_key(user):
    if user is not None and user.is_authenticated:
        return user.uuid.hex

    return None


def auth_login(request, user, backend=None):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    session_auth_hash = ''
    if user is None:
        user = request.user

    session_auth_hash = get_session_auth_hash(user)
    expiry = getattr(user, '_auth_session_expiry', 0)
    device_id = getattr(user, '_auth_device_id', None)

    if SESSION_KEY in request.session:
        if _get_user_session_key(request) != _get_user_key(user) or \
                (session_auth_hash and request.session.get(HASH_SESSION_KEY) != session_auth_hash):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()

    try:
        backend = backend or user.backend
    except AttributeError:
        backends = _get_backends(return_tuples=True)
        if len(backends) == 1:
            _, backend = backends[0]
        else:
            raise ValueError(
                'You have multiple authentication backends configured and '
                'therefore must provide the `backend` argument or set the '
                '`backend` attribute on the user.'
            )

    request.session[SESSION_KEY] = _get_user_key(user)
    request.session[BACKEND_SESSION_KEY] = backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    request.session[SESSION_AUTH_DATE] = int(time.time())
    if device_id:
        request.session[DEVICE_KEY] = device_id
    request.session.set_expiry(expiry)

    if hasattr(request, 'user'):
        request.user = user
    rotate_token(request)
    user_logged_in.send(sender=user.__class__, request=request, user=user)


def is_otp_login(user, is_two_factor_required):
    if hasattr(user, 'sso_auth_profile'):
        profile = user.sso_auth_profile
        if (profile.default_device and profile.is_otp_enabled) or (profile.default_device and is_two_factor_required):
            return profile.default_device

    if is_two_factor_required:
        # if the user has not enabled two_factor as default but a confirmed device
        # we return the first device of the user
        return user.device_set.filter(confirmed=True).first()

    return None


def get_session_auth_hash(user, client=None):
    # Returns an HMAC of the password and client_secret field.
    if user is None:
        logger.debug("get_session_auth_hash with user == None")
        return ""
    key_salt = HASH_SESSION_KEY
    data = user.password
    if client is not None:
        data += client.client_secret
    return salted_hmac(key_salt, data).hexdigest()


def update_session_auth_hash(request, user):
    """
    Updating a user's password logs out all sessions for the user

    This function takes the current request and the updated user object from
    which the new session hash will be derived and updates the session hash
    appropriately to prevent a password change from logging out the session
    from which the password was changed.
    """
    if request.user == user:
        request.session[HASH_SESSION_KEY] = get_session_auth_hash(user)


def get_user(request, client=None):
    """
    Returns the user model instance associated with the given request session.
    If no user is retrieved an instance of `AnonymousUser` is returned.
    """
    from django.contrib.auth.models import AnonymousUser
    user = None
    try:
        user_id = _get_user_session_key(request)
        backend_path = request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            session_hash = request.session.get(HASH_SESSION_KEY)
            session_hash_verified = session_hash and constant_time_compare(
                session_hash,
                get_session_auth_hash(user, client)
            )
            if not session_hash_verified:
                request.session.flush()
                user = None

    return user or AnonymousUser()
