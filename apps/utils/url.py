# -*- coding: utf-8 -*-
import urlparse
import urllib

from django.contrib.sites.shortcuts import get_current_site

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


def base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def absolute_url(request, url):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    if not scheme:
        scheme = 'https' if request.is_secure() else 'http'
    if not netloc:
        netloc = get_current_site(request).domain
    
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))
