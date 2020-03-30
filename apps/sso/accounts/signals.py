import datetime

from ipware.ip import get_real_ip

from django.conf import settings
from django.contrib.auth import user_logged_in
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from django.utils.timezone import now
from sso.accounts.models import User, UserEmail
from sso.organisations.models import is_validation_period_active_for_user
from sso.signals import user_m2m_field_updated
from sso.utils.loaddata import disable_for_loaddata


@receiver(post_save, sender=User)
@disable_for_loaddata
def update_user(sender, instance, created, **kwargs):
    if created and instance.last_modified_by_user:
        instance.created_by_user = instance.last_modified_by_user
        instance.save()


@receiver(post_save, sender=UserEmail)
def update_last_modified(sender, instance, created, **kwargs):
    """
    A signal receiver which updates the last_modified date for
    the user.
    """
    user = instance.user
    user.last_modified = timezone.now()
    user.save(update_fields=['last_modified'])


@receiver(user_logged_in)
def update_last_login_and_ip(sender, user, **kwargs):
    """
    A signal receiver which updates the last_ip IP Address and last_login for
    the user logging in.
    """
    user.last_login = timezone.now()
    update_fields = ['last_login']

    if 'request' in kwargs:
        user.last_ip = get_real_ip(kwargs['request'])
        update_fields.append('last_ip')

    user.save(update_fields=update_fields)


@receiver(user_m2m_field_updated, dispatch_uid="sso_user_m2m_field_updated")
def sso_user_m2m_field_updated(sender, user, attribute_name, delete_pk_list, add_pk_list, **kwargs):
    if attribute_name == 'organisations':
        # the caller must save the data to the database
        if is_validation_period_active_for_user(user) and user.valid_until is None:
            user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        elif not is_validation_period_active_for_user(user) and user.valid_until is not None:
            user.valid_until = None
