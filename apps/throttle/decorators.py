import hashlib
import logging
import os
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from ipware import get_client_ip

logger = logging.getLogger(__name__)


class HttpResponseTooManyRequests(HttpResponse):
    status_code = 403  # maybe 429 is better?


def throttle(method='POST', duration=15, max_calls=1, response=None, key_fields=None):
    """
    This decorator is based on Django snippet #1573 code that
    can be found at http://djangosnippets.org/snippets/1573/

    Simple usage

        @throttle
        def my_view(request):
            ""

    You can specify each of HTTP method

        @throttle(method='GET')
        def my_get_view(request)
            ""

    Custom

    """
    def decorator(func):
        if response:
            if not isinstance(response, HttpResponse) and not callable(response):
                raise TypeError("The `response` keyword argument must " +
                                "be a either HttpResponse instance or " +
                                "callable with `request` argument.    ")

        @wraps(func)
        def inner(request, *args, **kwargs):
            if request.method == method and not os.environ.get('THROTTLING_DISABLED', 'False').lower() in ('true', '1', 't'):
                # Determine the real client IP via ipware instead of trusting the
                # raw X-Forwarded-For header. Set SSO_THROTTLE_PROXY_COUNT to the
                # number of trusted reverse proxies so a client cannot spoof
                # X-Forwarded-For to get a fresh counter for every request.
                client_ip, _ = get_client_ip(request, proxy_count=settings.SSO_THROTTLE_PROXY_COUNT)
                remote_addr = client_ip or request.META.get('REMOTE_ADDR')
                # Temporary aid for choosing SSO_THROTTLE_PROXY_COUNT: when
                # SSO_THROTTLE_PROXY_DEBUG is on, log the raw X-Forwarded-For and
                # the client IP ipware resolves for each candidate proxy_count.
                # Call from OUTSIDE without setting X-Forwarded-For yourself: the
                # smallest proxy_count whose resolved IP is your real public IP
                # is the value to configure. Turn this off in production.
                if getattr(settings, 'SSO_THROTTLE_PROXY_DEBUG', False):
                    xff = request.META.get('HTTP_X_FORWARDED_FOR')
                    resolved = {
                        pc: get_client_ip(request, proxy_count=pc)[0]
                        for pc in (None, 0, 1, 2, 3)
                    }
                    logger.warning(
                        'throttle proxy-debug path=%s REMOTE_ADDR=%s '
                        'X-Forwarded-For=%r configured_proxy_count=%s resolved=%s',
                        request.path, request.META.get('REMOTE_ADDR'), xff,
                        settings.SSO_THROTTLE_PROXY_COUNT, resolved,
                    )
                # Key on the path only, never the query string, otherwise an
                # attacker can append ?x=<random> to bypass the throttle.
                # NB: reliable throttling across workers needs a shared cache
                # (set CACHES_LOCATION); the local-memory cache counts per process.
                path = request.path
                # Optionally include request fields (e.g. the login identifier) in
                # the key, so different accounts behind a shared IP/NAT get their
                # own counter and do not throttle each other. Values are normalised
                # (strip + lower) so case/whitespace variations can't get a fresh
                # counter for the same account.
                extra = ''
                if key_fields:
                    values = [request.POST.get(f, request.GET.get(f, '')).strip().lower() for f in key_fields]
                    extra = '.' + '.'.join(values)
                key = hashlib.md5('{addr}.{path}{extra}'.format(addr=remote_addr, path=path, extra=extra).encode('utf-8')).hexdigest()

                called = cache.get(key, 0) + 1

                if called > max_calls:
                    if callable(response):
                        return response(request)
                    elif response:
                        return response
                    else:
                        logger.warning('throttling client: %s:%s', remote_addr, path)
                        return HttpResponseTooManyRequests('Try slowing down a little.')

                cache.set(key, called, duration)
            return func(request, *args, **kwargs)
        return inner
    return decorator
