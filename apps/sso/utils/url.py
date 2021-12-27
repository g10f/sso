import logging
import uuid
from urllib.parse import urlsplit, urlunsplit

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


def get_safe_redirect_uri(request, allowed_hosts, redirect_field_name=REDIRECT_URI_FIELD_NAME):
    # redirect_field_name may be an array of field names
    if isinstance(redirect_field_name, list):
        for field_name in redirect_field_name:
            redirect_uri = get_request_param(request, field_name)
            if redirect_uri is not None:
                break
    else:
        redirect_uri = get_request_param(request, redirect_field_name)

    if redirect_uri is not None:
        if is_safe_url(redirect_uri, allowed_hosts=allowed_hosts):
            state = get_request_param(request, 'state')
            if state is not None:
                redirect_uri = update_url(redirect_uri, {'state': state})
            return redirect_uri
        else:
            logger.warning("redirect_uri %s is not safe, allowed_hosts: %s", redirect_uri, allowed_hosts)
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


def remove_value_from_url_param(url, param, value):
    """Given a URL removes a value from the param.

    >>> remove_value_from_url_param('http://example.com?prompt=login%20consent&foo=sample', 'prompt', 'login')
    'http://example.com?prompt=consent&foo=sample'
    """
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    q = QueryDict(query, mutable=True)

    if param in q:
        values = q[param].split()
        if value in values:
            values.remove(value)
        q[param] = ' '.join(values)

    new_query_string = q.urlencode(safe='/')
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


base_url = f"{'https' if settings.SSO_USE_HTTPS else 'http'}://{settings.SSO_DOMAIN}"


def get_base_url(request=None):
    if request:
        domain = get_current_site(request).domain
        use_https = request.is_secure()
        url = '%s://%s' % ('https' if use_https else 'http', domain)
        if not settings.RUNNING_TEST:
            if use_https != settings.SSO_USE_HTTPS:
                logger.error('Please check your SSO_USE_HTTPS setting. %s != %s. Headers=%s', use_https,
                             settings.SSO_USE_HTTPS, request.headers)
            if domain.lower().split(':')[0] != settings.SSO_DOMAIN.lower().split(':')[0]:
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
