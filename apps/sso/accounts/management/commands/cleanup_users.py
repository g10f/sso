# -*- coding: utf-8 -*-
import os
import logging
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
        # print("SSO_VALIDATION_PERIOD_IS_ACTIVE is False")
        return

    try:
        guest_profile = RoleProfile.objects.get(uuid=settings.SSO_DEFAULT_GUEST_PROFILE_UUID)
    except ObjectDoesNotExist:
        # print("no SSO_DEFAULT_GUEST_PROFILE_UUID available")
        return

    profiles = [guest_profile]
    has_already_guest_status = Q(application_roles=None) & Q(c=len(profiles))
    for profile in profiles:
        has_already_guest_status &= Q(role_profiles=profile)

    q = Q(valid_until__isnull=True) | has_already_guest_status
    users = User.objects.annotate(c=Count('role_profiles')).filter(valid_until__lt=now()).exclude(q)
    if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL:
        users = users.filter(organisations__uses_user_activation=True)

    # print("Assigning guest status to:")
    for user in users:
        user.application_roles = []
        user.role_profiles = [guest_profile]
        # print(" %s" % user)


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
