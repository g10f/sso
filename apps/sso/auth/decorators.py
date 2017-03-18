from django.core.urlresolvers import reverse_lazy
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from functools import wraps

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.utils.decorators import available_attrs
from django.utils.six.moves.urllib.parse import urlparse
from sso.auth.utils import is_recent_auth_time
from sso.auth.views import TWO_FACTOR_PARAM
from sso.utils.url import update_url


def request_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Same as django.contrib.auth.decorators.user_passes_test with passing the request
    to the test_func instead of the user object
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
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
        login_url = update_url(reverse_lazy('login'), {TWO_FACTOR_PARAM: '1'})
    test = lambda u: u.is_authenticated and u.is_verified
    actual_decorator = user_passes_test(
        test,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
