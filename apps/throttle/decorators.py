# -*- coding: utf-8 -*-
from functools import wraps
import hashlib

from django.core.cache import cache
from django.utils.decorators import available_attrs
from django.http import HttpResponseForbidden, HttpResponse

import logging
logger = logging.getLogger(__name__)

def throttle(method='POST', duration=15, max_calls=1, response=None):
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
            if not isinstance(response, HttpResponse) and  not callable(response):
                raise TypeError("The `response` keyword argument must " + \
                                 "be a either HttpResponse instance or " + \
                                 "callable with `request` argument.    ")
        
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            if request.method == method:
                remote_addr = request.META.get('HTTP_X_FORWARDED_FOR') or \
                              request.META.get('REMOTE_ADDR')
                path = request.get_full_path()
                key = hashlib.md5('{addr}.{path}'.format(addr=remote_addr, path=path)).hexdigest()
                
                called = cache.get(key, 0) + 1
                
                if called > max_calls:
                    if callable(response):
                        return response(request)    
                    elif response:
                        return response    
                    else:
                        logger.warning('throttling client: %s:%s', remote_addr, path)
                        return HttpResponseForbidden('Try slowing down a little.')
                
                cache.set(key, called, duration)
            return func(request, *args, **kwargs)
        return inner
    return decorator
