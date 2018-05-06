import os
import logging

from datetime import timedelta

from django.db.models.aggregates import Count
from django.db.models.query_utils import Q

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from sso.accounts.models import User, RoleProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup Users'  # @ReservedAssignment

    def handle(self, *args, **options):
        check_validation()


def check_validation():
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
        return

    try:
        guest_profile = RoleProfile.objects.get(uuid=settings.SSO_DEFAULT_GUEST_PROFILE_UUID)
    except ObjectDoesNotExist:
        return

    # 1. Assign Guest Profile to expired user accounts
    has_already_guest_status = Q(application_roles=None) & Q(count_profiles=1) & Q(role_profiles=guest_profile)
    expired_users = User.objects.annotate(count_profiles=Count('role_profiles')).\
        filter(valid_until__lt=now()).\
        exclude(has_already_guest_status)
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
        expired_users = expired_users.filter(organisations__uses_user_activation=True)

    logger.info("Expired Users:")
    logger.debug("-----------------------------------------")
    for expired_user in expired_users:
        expired_user.application_roles.clear()
        expired_user.role_profiles.set([guest_profile])
        logger.debug("%s" % expired_user)

    # 2. user with valid_until__isnull=True and a center which uses user activation will expire in 30 days
    new_users = User.objects.annotate(count_profiles=Count('role_profiles'))\
        .filter(is_active=True, valid_until__isnull=True, is_service=False, is_center=False,
                organisations__uses_user_activation=True)

    logger.debug("new Users:")
    logger.debug("-----------------------------------------")
    for new_user in new_users:
        new_user.valid_until = now() + timedelta(days=30)
        new_user.save(update_fields=['valid_until'])
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
