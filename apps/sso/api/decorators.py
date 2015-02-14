# -*- coding: utf-8 -*-
from functools import wraps
from calendar import timegm
import logging

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, ValidationError
from django.utils.decorators import available_attrs
from django.utils.http import http_date, parse_http_date_safe, parse_etags, quote_etag
from django.http import HttpResponseNotModified, HttpResponse

from sso.api.response import HttpApiResponseNotAuthorized, HttpApiErrorResponse


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
        except ObjectDoesNotExist as e:
            logger.warning('ObjectDoesNotExist caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error='not_found', error_description=str(e), request=request, status_code=404)
        except ValueError as e:
            logger.warning('ValueError caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error='bad_request', error_description=str(e), request=request, status_code=400)
        except ValidationError as e:
            logger.warning('ValidationError caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error='bad_request', error_description=str(e), request=request, status_code=400)
        except AttributeError as e:
            logger.warning('AttributeError caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error='bad_request', error_description=str(e), request=request, status_code=400)
        except Exception as e:
            logger.warning('Exception caught while processing request, %s.' % e)
            return HttpApiErrorResponse(error_description=str(e), request=request)
    return _wrapped_view


def condition(last_modified_and_etag_func=None):
    """
    see condition from django.views.decorators.http
    
    what is changed?
    for put, patch and post request, the etag and last_modified are fresh created  
    at the end of the function
    
    from django original:
    Decorator to support conditional retrieval (or change) for a view
    function.

    The parameters are callables to compute the ETag and last modified time for
    the requested resource, respectively. The callables are passed the same
    parameters as the view itself. The Etag function should return a string (or
    None if the resource doesn't exist), whilst the last_modified function
    should return a datetime object (or None if the resource doesn't exist).

    If both parameters are provided, all the preconditions must be met before
    the view is processed.

    This decorator will either pass control to the wrapped view function or
    return an HTTP 304 response (unmodified) or 412 response (preconditions
    failed), depending upon the request method.

    Any behavior marked as "undefined" in the HTTP spec (e.g. If-none-match
    plus If-modified-since headers) will result in the view function being
    called.
    """
    def get_last_modified_and_etag_func(last_modified_and_etag_func, request, *args, **kwargs):
        if last_modified_and_etag_func:
            dt, res_etag = last_modified_and_etag_func(request, *args, **kwargs)
            if dt:
                res_last_modified = timegm(dt.utctimetuple())
            else:
                res_last_modified = None
        else:
            res_etag = None
            res_last_modified = None
        return res_last_modified, res_etag
    
    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            # Get HTTP request headers
            if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
            if if_modified_since:
                if_modified_since = parse_http_date_safe(if_modified_since)
            if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
            if_match = request.META.get("HTTP_IF_MATCH")
            if if_none_match or if_match:
                # There can be more than one ETag in the request, so we
                # consider the list of values.
                try:
                    etags = parse_etags(if_none_match or if_match)
                except ValueError:
                    # In case of invalid etag ignore all ETag headers.
                    # Apparently Opera sends invalidly quoted headers at times
                    # (we should be returning a 400 response, but that's a
                    # little extreme) -- this is Django bug #10681.
                    if_none_match = None
                    if_match = None

            # Compute values (if any) for the requested resource.
            res_last_modified, res_etag = get_last_modified_and_etag_func(last_modified_and_etag_func, request, *args, **kwargs)

            response = None
            if not ((if_match and (if_modified_since or if_none_match)) or
                    (if_match and if_none_match)):
                # We only get here if no undefined combinations of headers are
                # specified.
                if ((if_none_match and (res_etag in etags or
                                        "*" in etags and res_etag)) and
                        (not if_modified_since or
                            (res_last_modified and if_modified_since and
                             res_last_modified <= if_modified_since))):
                    if request.method in ("GET", "HEAD"):
                        response = HttpResponseNotModified()
                    else:
                        logger.warning('Precondition Failed: %s', request.path,
                                       extra={'status_code': 412, 'request': request}
                                       )
                        response = HttpResponse(status=412)
                elif if_match and ((not res_etag and "*" in etags) or
                                   (res_etag and res_etag not in etags)):
                    logger.warning('Precondition Failed: %s', request.path,
                                   extra={'status_code': 412, 'request': request}
                                   )
                    response = HttpResponse(status=412)
                elif (not if_none_match and request.method == "GET" and
                        res_last_modified and if_modified_since and
                        res_last_modified <= if_modified_since):
                    response = HttpResponseNotModified()

            if response is None:
                response = func(request, *args, **kwargs)
            
            # refresh last_modified and res_etag if needed
            if (request.method in ("PUT", "POST", "PATCH")) and (
                (res_last_modified and not response.has_header('Last-Modified')) or
                    (res_etag and not response.has_header('ETag'))):  # refresh last_modified and res_etag!
                res_last_modified, res_etag = get_last_modified_and_etag_func(last_modified_and_etag_func, request, *args, **kwargs)

            # Set relevant headers on the response if they don't already exist.
            if res_last_modified and not response.has_header('Last-Modified'):
                response['Last-Modified'] = http_date(res_last_modified)
            if res_etag and not response.has_header('ETag'):
                response['ETag'] = quote_etag(res_etag)

            return response

        return inner
    return decorator
