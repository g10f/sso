import logging
from urllib.parse import urlsplit, urlunsplit

import uuid

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import QueryDict
from django.utils.http import is_safe_url
from sso.utils.http import get_request_param

logger = logging.getLogger(__name__)

REDIRECT_URI_FIELD_NAME = 'redirect_uri'


class UUIDConverter:
    """
    UUID converter which accepts uuids with or without hyphens
    """
    regex = '[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def to_python(self, value):
        return uuid.UUID(value)

    def to_url(self, value):
        return str(value)


def get_safe_redirect_uri(request, hosts, redirect_field_name=REDIRECT_URI_FIELD_NAME):
    redirect_uri = get_request_param(request, redirect_field_name)
    if is_safe_url(redirect_uri, allowed_hosts=set(hosts)):
        return redirect_uri
    else:
        return None


def update_url(url, params):
    """Given a URL, add or update query parameter and return the
    modified URL.

    >>> update_url('http://example.com?foo=bar&biz=baz', {'foo': 'stuff', 'new': 'val'})
    'http://example.com?foo=stuff&biz=baz&new=val'

    """
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    q = QueryDict(query, mutable=True)

    for k, v in params.items():
        if v is not None:  # filter out None values
            q[k] = str(v)

    new_query_string = q.urlencode(safe='/')
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


base_url = '%s://%s' % ('https' if settings.SSO_USE_HTTPS else 'http', settings.SSO_DOMAIN)


def get_base_url(request=None):
    if request:
        domain = get_current_site(request).domain
        use_https = request.is_secure()
        url = '%s://%s' % ('https' if use_https else 'http', domain)
        if not settings.RUNNING_TEST:
            if use_https != settings.SSO_USE_HTTPS:
                logger.error('Please check your SSO_USE_HTTPS setting. %s != %s', use_https, settings.SSO_USE_HTTPS)
            if domain.lower() != settings.SSO_DOMAIN.lower():
                logger.error('Please check your SSO_DOMAIN setting. %s != %s', domain, settings.SSO_DOMAIN)
        return url
    return base_url


def absolute_url(request, url):
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    if not scheme:
        scheme = 'https' if request.is_secure() else 'http'
    if not netloc:
        netloc = get_current_site(request).domain

    return urlunsplit((scheme, netloc, path, query, fragment))
