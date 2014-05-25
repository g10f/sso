# -*- coding: utf-8 -*-
from django.utils.functional import SimpleLazyObject, empty
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from .crypt import loads_jwt
from .models import Client

import logging
logger = logging.getLogger(__name__)


class IterableLazyObject(SimpleLazyObject):
    def __iter__(self):
        if self._wrapped is empty:
            self._setup()
        return self._wrapped.__iter__()


def get_user_and_client_from_token(access_token):
    try:
        if not access_token:
            return (auth.models.AnonymousUser(), None, set())
        data = loads_jwt(access_token)
        user = get_user_model().objects.get(uuid=data['sub'])
        client = Client.objects.get(uuid=data['aud'])
        scopes = set()
        if data.get('scope'):
            scopes = set(data['scope'].split())
    except (ObjectDoesNotExist, signing.BadSignature, ValueError):
        return (auth.models.AnonymousUser(), None, set())
    return (user, client, scopes)


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
            access_token = None
            http_authorization = request.META.get('HTTP_AUTHORIZATION')
            if http_authorization:
                http_authorization = http_authorization.split()
                if http_authorization[0] == 'Bearer':
                    access_token = http_authorization[1]
            else:
                access_token = request.REQUEST.get('access_token')
            if access_token:
                request._cached_auth_data = get_user_and_client_from_token(access_token)
        
        if not hasattr(request, '_cached_auth_data'):
            # try django auth session
            request._cached_auth_data = auth.get_user(request), None, set(['address', 'phone'])
    return request._cached_auth_data


class OAuthAuthenticationMiddleware(object):
    def process_request(self, request):            
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."

        request.user = SimpleLazyObject(lambda: get_auth_data(request)[0])
        request.client = SimpleLazyObject(lambda: get_auth_data(request)[1])
        request.scopes = IterableLazyObject(lambda: get_auth_data(request)[2])
