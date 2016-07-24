from datetime import timedelta

from django import template
from django.utils.timezone import now

register = template.Library()


@register.filter
def valid_until_class(user):
    """
    return alert-danger if account has expired and alert-warning if
    the account will expire in the next 30 days
    """
    if not user.valid_until or (user.valid_until > now() + timedelta(days=30)):
        return ''
    elif user.valid_until > now():
        return 'alert alert-warning'
    else:
        return 'alert alert-danger'
