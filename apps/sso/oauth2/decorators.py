# -*- coding: utf-8 -*-
try:
    from urllib.parse import urlparse, urlunparse, urlsplit, urlunsplit
except ImportError:     # Python 2
    from urlparse import urlparse, urlunparse, urlsplit, urlunsplit
    
from functools import wraps
from django.utils.decorators import available_attrs
from django.core.exceptions import PermissionDenied
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.utils.encoding import force_str
from django.shortcuts import resolve_url
from django.utils import timezone

import logging

 
logger = logging.getLogger(__name__)
from django.http import HttpResponseRedirect, QueryDict

def extract_query_param(url, attr):    
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    query_dict = QueryDict(query).copy()
    # get the last value 
    value = query_dict.get(attr, None) 
    if value:
        del query_dict[attr]
    query = query_dict.urlencode()
    return urlunsplit((scheme, netloc, path, query, fragment)), value


def redirect_to_login_and_extract_display_param(next, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):  # @ReservedAssignment
    """
    Redirects the user to the login page, passing the given 'next' page
    if there is a display parameter in the url we extract this parameter from the next url
    and pass it directly to the login url
    """
    resolved_url = resolve_url(login_url or settings.LOGIN_URL)
    
    next, display = extract_query_param(next, 'display')  # @ReservedAssignment to next

    login_url_parts = list(urlparse(resolved_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        if display:
            querystring['display'] = display
            
        login_url_parts[4] = querystring.urlencode(safe='/')

    return HttpResponseRedirect(urlunparse(login_url_parts))


def login_required(view_func):
    """
    Copy of django.contrib.auth.decorators.login_required
    with the following changes:
    1. If there is a display parameter in the url, this parameter is extracted and 
    gets passed to the login url. 
    The display parameter changes the layout of the login form
    2. if there is a max_age param check ...
    """

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated():
            max_age = request.POST.get('max_age') if request.POST.get('max_age') else request.GET.get('max_age')
            if not max_age or (int(max_age) > (timezone.now() - request.user.last_login).total_seconds()):
                return view_func(request, *args, **kwargs)
        
        path = request.build_absolute_uri()
        # urlparse chokes on lazy objects in Python 3, force to str
        resolved_login_url = force_str(resolve_url(settings.LOGIN_URL))
        # If the login url is the same scheme and net location then just
        # use the path as the "next" url.
        login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
        current_scheme, current_netloc = urlparse(path)[:2]
        if ((not login_scheme or login_scheme == current_scheme) and
            (not login_netloc or login_netloc == current_netloc)):
            path = request.get_full_path()
        return redirect_to_login_and_extract_display_param(path, resolved_login_url)
    return _wrapped_view


def request_passes_test(test_func):
    """
    Decorator for views that checks that the request object passes the given test.
    The test should be a callable that takes the request object and returns True if the request passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator


def scopes_required(scopes):
    """
    Decorator for views that checks whether a token has particular scopes.
    """
    def check_scopes(request):
        if scopes:
            # check scopes
            required_scopes = set(scopes)
            if request.scopes:
                valid_scopes = request.scopes
                if required_scopes.issubset(valid_scopes):
                    return True

        raise PermissionDenied('required scopes not matching')
    return request_passes_test(check_scopes)


def client_required(client_uuids, raise_exception=False):
    """
    Decorator for views that checks whether a token has particular scopes.
    """
    def check_client(request):
        if client_uuids:
            if request.client and request.client.uuid in client_uuids:
                return True

        raise PermissionDenied('client_id not allowed')
    return request_passes_test(check_client)
