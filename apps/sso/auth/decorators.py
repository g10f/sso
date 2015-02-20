from datetime import timedelta

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import now


def admin_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None, max_age=None):
    """
    Decorator for views that checks that the user is logged in and the login is not older
    than max_age, redirecting to the log-in page if necessary.
    """
    if max_age is None:
        max_age = settings.SSO_ADMIN_MAX_AGE

    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated() and now() - u.last_login < timedelta(seconds=max_age),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
