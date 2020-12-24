import calendar
import logging
from functools import lru_cache
from urllib.parse import urlsplit

import time

from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.encoding import force_str
from django.utils.module_loading import import_string
from sso.auth import get_session_auth_hash, HASH_SESSION_KEY
from .crypt import make_jwt, MAX_AGE

logger = logging.getLogger(__name__)


def get_iss_from_absolute_uri(abs_uri):
    (scheme, netloc, path, query, fragment) = urlsplit(abs_uri)  # @UnusedVariable
    return "%s://%s" % (scheme, netloc)


def get_token_claim_set(request, max_age=MAX_AGE):
    user = request.user
    claim_set = {
        'jti': get_random_string(12),
        'iss': get_iss_from_absolute_uri(request.uri),
        'sub': user.uuid.hex,  # required
        'aud': request.client.client_id,  # required
        'exp': int(time.time()) + max_age,  # required
        'iat': int(time.time()),  # required
        'acr': '2' if user.is_verified else '1',
        'scope': ' '.join(request.scopes),  # custom, required
        'email': force_str(user.primary_email()),  # custom
        'name': user.username,  # custom
        # session authentication hash,
        HASH_SESSION_KEY: get_session_auth_hash(user, request.client),  # custom, required
    }
    if request.client.application:
        claim_set['roles'] = ' '.join(
            user.get_roles_by_app(request.client.application.uuid).values_list('name', flat=True))  # custom
    return claim_set


def default_token_generator(request, max_age=MAX_AGE):
    claim_set = get_token_claim_set(request, max_age)
    return make_jwt(claim_set)


def get_idtoken_claim_set(request, max_age=MAX_AGE):
    """
    The generated id_token contains additionally email, name and roles
    """
    user = request.user
    auth_time = int(calendar.timegm(user.last_login.utctimetuple()))
    claim_set = {
        'iss': get_iss_from_absolute_uri(request.uri),
        'sub': user.uuid.hex,
        'exp': int(time.time()) + max_age,
        'auth_time': auth_time,  # required when max_age is in the request
        'acr': '2' if user.is_verified else '1',
        'email': force_str(user.primary_email()),  # custom
        'name': user.username,  # custom
        'given_name': user.first_name,  # custom
        'family_name': user.last_name,  # custom
    }
    if request.client.application:
        claim_set['roles'] = ' '.join(
            user.get_roles_by_app(request.client.application.uuid).values_list('name', flat=True))  # custom
    return claim_set


# http://openid.net/specs/openid-connect-basic-1_0.html#IDToken
def default_idtoken_finalizer(id_token, token, token_handler, request):
    claim_set = get_idtoken_claim_set(request)
    id_token.update(claim_set)
    return make_jwt(id_token)


@lru_cache()
def get_idtoken_finalizer():
    idtoken_finalizer = import_string(settings.SSO_DEFAULT_IDTOKEN_FINALIZER)
    return idtoken_finalizer


@lru_cache()
def get_token_generator():
    token_generator = import_string(settings.SSO_DEFAULT_TOKEN_GENERATOR)
    return token_generator
