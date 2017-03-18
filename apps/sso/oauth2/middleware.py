# -*- coding: utf-8 -*-
from django.utils.deprecation import MiddlewareMixin
from jwt import InvalidTokenError
from django.utils.functional import SimpleLazyObject, empty
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import constant_time_compare
from django.contrib.auth.models import AnonymousUser
from django.conf import settings

from .crypt import loads_jwt
from .models import Client
from sso import auth as sso_auth


import logging
from sso.auth import get_session_auth_hash

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
        
        session_hash = data.get(sso_auth.HASH_SESSION_KEY)
        user = get_user_model().objects.get(uuid=data['sub'])
        session_hash_verified = session_hash and \
            constant_time_compare(session_hash, get_session_auth_hash(user, client))

        if not session_hash_verified:
            logger.error('session_ hash verification failed. jwt data: %s', data)
            return AnonymousUser(), None, set()
        scopes = set()
        if data.get('scope'):
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
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. \
        Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        request.user = SimpleLazyObject(lambda: get_auth_data(request)[0])
        request.client = SimpleLazyObject(lambda: get_auth_data(request)[1])
        request.scopes = IterableLazyObject(lambda: get_auth_data(request)[2])
