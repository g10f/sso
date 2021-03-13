from datetime import timedelta

from django import template
from django.utils.timezone import now

register = template.Library()


@register.filter
def valid_until_class(user):
    """
    return table-danger if account has expired and table-warning if
    the account will expire in the next 30 days
    """
    if not user.valid_until or (user.valid_until > now() + timedelta(days=30)):
        return ''
    elif user.valid_until > now():
        return 'table-warning'
    else:
        return 'table-danger'
