from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test


def admin_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None, max_age=None):
    """
    Decorator for views that checks that the user is logged in and the login is not older
    than max_age, redirecting to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_recent_auth_time(max_age),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
