from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from django.utils import timezone
from sso.accounts.models import User, UserEmail
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
