from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from sso.auth.utils import is_recent_auth_time


def request_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME, message=''):
    """
    Same as django.contrib.auth.decorators.user_passes_test with passing the request
    to the test_func instead of the user object
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            if message:
                messages.add_message(request, level=messages.ERROR, message=message, fail_silently=True)
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)

        return _wrapped_view

    return decorator


def admin_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None, max_age=None):
    """
    Decorator for views that checks that the user is logged in and the login is not older
    than max_age, redirecting to the log-in page if necessary.
    """
    actual_decorator = request_passes_test(
        lambda request: request.user.is_authenticated and is_recent_auth_time(request, max_age),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def otp_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator for views that checks that the user is logged in with 2FA, redirecting
    to the log-in page if necessary.
    """
    if login_url is None:
        login_url = reverse_lazy('auth:mfa-detail')
    actual_decorator = request_passes_test(
        lambda request: request.user.is_authenticated and request.user.is_verified,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
        message=_('2 Factor Authentication required!')
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
