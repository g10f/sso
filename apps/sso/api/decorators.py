# -*- coding: utf-8 -*-
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.decorators import available_attrs
from sso.http_status import *  # @UnusedWildImport
from sso.api.response import HttpApiResponseNotAuthorized, HttpApiErrorResponse

import logging

logger = logging.getLogger(__name__)

def api_user_passes_test(test_func):
    """
    Decorator for views that checks that the user passes the given test,
    returning HTTP 401  if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            else:
                return HttpApiResponseNotAuthorized(request=request)
        return _wrapped_view
    return decorator


def catch_errors(view_func):
    """
    Decorator for views that catches Exception and returns a json response,
    with error information. The json response is with respect to a possible 
    jsonp request, which does not handle HTTP Errors.
    """
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except PermissionDenied as e:
            logger.warning('PermissionDenied caught while processing request, %s.' % e)
            return HttpApiResponseNotAuthorized(error_description=str(e), request=request)
        except Exception as e:
            logger.warning('Exception caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error_description=str(e), request=request)
    return _wrapped_view
