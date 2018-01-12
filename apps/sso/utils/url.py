import logging
from urllib.parse import urlparse, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import QueryDict
from sso.utils.http import get_request_param

logger = logging.getLogger(__name__)

REDIRECT_URI_FIELD_NAME = 'redirect_uri'


def get_safe_redirect_uri(request, hosts, redirect_field_name=REDIRECT_URI_FIELD_NAME):
    redirect_uri = get_request_param(request, redirect_field_name)
    if not is_safe_ext_url(redirect_uri, set(hosts)):
        return None
    else:
        return redirect_uri


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
            q[k] = v

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


def is_safe_ext_url(url, hosts):
    """
    like django.util.http.is_safe_url but with a list of hosts instead one host name

    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).

    Always returns ``False`` on an empty url.
    """
    if not url:
        return False
    url = url.strip()
    # Chrome treats \ completely as /
    url = url.replace('\\', '/')
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith('///'):
        return False
    url_info = urlparse(url)
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    return ((not url_info.netloc or url_info.netloc in hosts) and
            (not url_info.scheme or url_info.scheme in ['http', 'https']))
