import logging
import os
from datetime import timedelta

import reversion

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q
from django.utils.timezone import now
from sso.accounts.models import User, RoleProfile, UserManager
from sso.registration.models import RegistrationManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup Users'  # @ReservedAssignment

    def handle(self, *args, **options):
        delete_deactivated_users()
        check_validation()


def delete_deactivated_users():
    with reversion.create_revision():
        recovery_expiration_date = UserManager.recovery_expiration_date()
        activation_expiration_date = RegistrationManager.activation_expiration_date()
        reversion.set_comment("Deleting deactivated accounts in cleanup_users task")
        q = (Q(last_login__isnull=True) | Q(last_login__lte=recovery_expiration_date))
        q = q & Q(is_active=False) & Q(last_modified__lte=recovery_expiration_date)
        q = q & (  # Users who did not registered themselve
                Q(registrationprofile__isnull=True) |
                # Users who registered themselve before activation_expiration_date
                Q(registrationprofile__date_registered__lte=activation_expiration_date) &
                Q(registrationprofile__is_access_denied=False))

        count = 0
        for user in User.objects.filter(q):
            logger.debug(f"Deleting {user}")
            user.delete()
            count += 1
        logger.debug(f"Deleted {count} user(s)")


def check_validation():
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
        return

    try:
        guest_profile = RoleProfile.objects.get(uuid=settings.SSO_DEFAULT_GUEST_PROFILE_UUID)
    except ObjectDoesNotExist:
        return

    # 1. Assign Guest Profile to expired user accounts
    guest_users = User.objects.annotate(count_profiles=Count('role_profiles')).filter(
        Q(application_roles=None) & Q(role_profiles=guest_profile) & Q(count_profiles=1))

    expired_users = User.objects.filter(valid_until__lt=now()).exclude(pk__in=guest_users)
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
        expired_users = expired_users.filter(organisations__uses_user_activation=True)

    logger.info("Expired Users:")
    logger.debug("-----------------------------------------")
    with reversion.create_revision():
        reversion.set_comment("cleared application_roles and set guest_profile in cleanup_users task")
        for expired_user in expired_users:
            expired_user.application_roles.clear()
            expired_user.role_profiles.set([guest_profile])
            expired_user.update_last_modified()
            logger.debug("%s" % expired_user)

    # 2. user with valid_until__isnull=True and a organisation which uses user activation will expire in 30 days
    new_users = User.objects.filter(is_active=True, valid_until__isnull=True, is_service=False, is_center=False)
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
        new_users = new_users.filter(organisations__uses_user_activation=True)

    logger.debug("new Users:")
    logger.debug("-----------------------------------------")
    with reversion.create_revision():
        reversion.set_comment("set valid_until in cleanup_users task")
        for new_user in new_users:
            new_user.valid_until = now() + timedelta(days=30)
            new_user.save(update_fields=['valid_until', 'last_modified'])
            logger.debug("%s" % new_user)


def clean_pictures():
    for basedir, dirs, _ in os.walk(os.path.join(settings.MEDIA_ROOT, 'image')):
        for d in dirs:
            try:
                picture = User.objects.get(uuid=d).picture
            except ObjectDoesNotExist:
                continue

            for subdir, _, files in os.walk(os.path.join(basedir, d)):
                for f in files:
                    fname1 = os.path.join(subdir, f)
                    fname2 = os.path.join(settings.MEDIA_ROOT, str(picture))
                    if not os.path.samefile(fname1, fname2):
                        print(fname1)
                        os.remove(fname1)
