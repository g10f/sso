import logging
import time

from jwt import InvalidTokenError

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import SuspiciousOperation
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject, empty
from django.utils.http import http_date
from sso import auth as sso_auth
from sso.auth import verify_session_auth_hash
from .crypt import loads_jwt
from .models import Client
from .views import get_oidc_session_state

logger = logging.getLogger(__name__)


class IterableLazyObject(SimpleLazyObject):
    def __iter__(self):
        if self._wrapped is empty:
            self._setup()
        return self._wrapped.__iter__()


def get_access_token(request):
    http_authorization = request.META.get('HTTP_AUTHORIZATION')
    if http_authorization:
        http_authorization = http_authorization.split()
        if len(http_authorization) == 2:
            if http_authorization[0] == 'Bearer':
                return http_authorization[1]
        return None
    else:
        return request.POST.get('access_token', request.GET.get('access_token', None))


def get_auth_data_from_token(access_token):
    try:
        if not access_token:
            return AnonymousUser(), None, set()
        data = loads_jwt(access_token)
        client = Client.objects.get(uuid=data['aud'])

        user = get_user_model().objects.get(uuid=data['sub'])
        session_hash_verified = verify_session_auth_hash(data, user, client)

        if not session_hash_verified:
            logger.warning('session_ hash verification failed. jwt data: %s', data)
            return AnonymousUser(), None, set()
        scopes = set()
        if 'scope' in data:
            scopes = set(data['scope'].split())
    except (ObjectDoesNotExist, InvalidTokenError, ValueError) as e:
        logger.warning(e)
        return AnonymousUser(), None, set()
    return user, client, scopes


def get_auth_data_from_cookie(request, with_client_and_scopes=False):
    client = None
    scopes = set()
    if with_client_and_scopes:  # get a client id for using the API in the Browser
        try:
            client = Client.objects.get(uuid=settings.SSO_BROWSER_CLIENT_ID)
            scopes = set(client.scopes.split())
        except ObjectDoesNotExist:
            pass

    user = sso_auth.get_user(request)
    return user, client, scopes


def get_auth_data(request):
    """
    Look for

    1. Authorization Header if path starts with /api/
    2. access_token Parameter if path starts with /api/
    3. Standard django session_id

    for authentication information

    """
    if not hasattr(request, '_cached_auth_data'):
        if request.path[:5] == '/api/':
            access_token = get_access_token(request)
            if access_token:
                auth_data = get_auth_data_from_token(access_token)
            else:
                auth_data = get_auth_data_from_cookie(request, with_client_and_scopes=True)
        else:
            auth_data = get_auth_data_from_cookie(request, with_client_and_scopes=False)
        request._cached_auth_data = auth_data
    return request._cached_auth_data


class OAuthAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be " \
                                            "installed. Edit your MIDDLEWARE_CLASSES setting to insert " \
                                            "'django.contrib.sessions.middleware.SessionMiddleware'."

        request.user = SimpleLazyObject(lambda: get_auth_data(request)[0])
        request.client = SimpleLazyObject(lambda: get_auth_data(request)[1])
        request.scopes = IterableLazyObject(lambda: get_auth_data(request)[2])


class SsoSessionMiddleware(SessionMiddleware):
    def process_response(self, request, response):
        """
        If request.session was modified, or if the configuration is to save the
        session every time, save the changes and set a session cookie or delete
        the session cookie if the session has been emptied.
        """
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        # First check if we need to delete this cookie.
        # The session should be deleted only if the session is entirely empty.
        if settings.SESSION_COOKIE_NAME in request.COOKIES and empty:
            response.delete_cookie(
                settings.SESSION_COOKIE_NAME,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            response.delete_cookie(
                settings.SSO_OIDC_SESSION_COOKIE_NAME,
                path=reverse('oauth2:session'),
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite='None' if settings.SESSION_COOKIE_SECURE else 'Lax',
            )
            patch_vary_headers(response, ('Cookie',))
        else:
            if accessed:
                patch_vary_headers(response, ('Cookie',))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)
                # Save the session data and refresh the client cookie.
                # Skip session save for 500 responses, refs #3881.
                if response.status_code != 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SuspiciousOperation(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        settings.SESSION_COOKIE_NAME,
                        request.session.session_key, max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    response.set_cookie(
                        settings.SSO_OIDC_SESSION_COOKIE_NAME,
                        get_oidc_session_state(request), max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path=reverse('oauth2:session'),
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=False,
                        samesite='None' if settings.SESSION_COOKIE_SECURE else 'Lax',
                    )
        return response
