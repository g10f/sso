# -*- coding: utf-8 -*-
import urlparse
import urllib
import functools

#from django.core.exceptions import PermissionDenied
#from django.http import HttpResponse
from django.contrib.sites.models import get_current_site
#from oauthlib import oauth2

import logging

logger = logging.getLogger(__name__)


def build_url(url, params):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_params = urlparse.parse_qs(query)
    query_params.update(params)
    new_query_string = urllib.urlencode(query_params, doseq=True)
    return urlparse.urlunsplit((scheme, netloc, path, new_query_string, fragment))


def is_safe_url(url, host=None):
    """
    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).

    Always returns ``False`` on an empty url.
    """
    if not url:
        return False
    url_info = urlparse.urlparse(url)
    return (not url_info.netloc or url_info.netloc == host) and \
        (not url_info.scheme or url_info.scheme in ['http', 'https'])

"""
def catch_errors(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kwargs):
        try:
            return f(request, *args, **kwargs)
        except PermissionDenied as e:
            logger.warning('PermissionDenied caught while processing request, %s.' % e)
            error = oauth2.AccessDeniedError(description=str(e))
            return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')
        except Exception as e:
            error = oauth2.ServerError(description=str(e))
            logger.warning('Exception caught while processing request, %s.' % e)
            return HttpResponse(content=error.json, status=error.status_code, content_type='application/json')
        
    return wrapper
"""

def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """
    @functools.wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if 'raw' in kwargs:
            return
        signal_handler(*args, **kwargs)
    return wrapper


def base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def absolute_url(request, url):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    if not scheme:
        scheme = 'https' if request.is_secure() else 'http'
    if not netloc:
        netloc = get_current_site(request).domain
    
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))
