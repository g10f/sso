# -*- coding: utf-8 -*-
from functools import wraps
from django.utils.decorators import available_attrs
from django.core.exceptions import PermissionDenied

import logging
logger = logging.getLogger(__name__)


def request_passes_test(test_func):
    """
    Decorator for views that checks that the request object passes the given test.
    The test should be a callable that takes the request object and returns True if the request passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator


def scopes_required(scopes):
    """
    Decorator for views that checks whether a token has particular scopes.
    """
    def check_scopes(request):
        if scopes:
            # check scopes
            required_scopes = set(scopes)
            if request.scopes:
                valid_scopes = request.scopes
                if required_scopes.issubset(valid_scopes):
                    return True

        raise PermissionDenied('required scopes not matching')
    return request_passes_test(check_scopes)


def client_required(client_uuids, raise_exception=False):
    """
    Decorator for views that checks whether a token has particular scopes.
    """
    def check_client(request):
        if client_uuids:
            if request.client and request.client.uuid.hex in client_uuids:
                return True

        raise PermissionDenied('client_id not allowed')
    return request_passes_test(check_client)
