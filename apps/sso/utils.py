# -*- coding: utf-8 -*-
import urlparse
import urllib
import functools

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.contrib.sites.models import get_current_site
from django.conf import settings
from oauthlib import oauth2

import logging

logger = logging.getLogger(__name__)


def build_url(url, params):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_params = urlparse.parse_qs(query)
    query_params.update(params)
    new_query_string = urllib.urlencode(query_params, doseq=True)
    return urlparse.urlunsplit((scheme, netloc, path, new_query_string, fragment))
    

def catch_errors(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kwargs):
        try:
            return f(request, *args, **kwargs)
        except PermissionDenied as e:
            logger.warning('PermissionDenied caught while processing request, %s.' % e)
            error = oauth2.AccessDeniedError(description=str(e))
            return HttpResponse(content=error.json, status=error.status_code)
        except Exception as e:
            error = oauth2.ServerError(description=str(e))
            logger.warning('Exception caught while processing request, %s.' % e)
            return HttpResponse(content=error.json, status=error.status_code)
        
    return wrapper


def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """
    @functools.wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs['raw']:
            return
        signal_handler(*args, **kwargs)
    return wrapper


def base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def absolute_media_url(request):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(settings.MEDIA_URL)
    if not scheme:
        scheme = 'https' if request.is_secure() else 'http'
    if not netloc:
        netloc = get_current_site(request).domain
    
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))
