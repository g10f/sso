# -*- coding: utf-8 -*-
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateformat import format

from utils.ucsv import UnicodeReader, UnicodeWriter, dic_from_csv

from sso.accounts.models import User, RoleProfile

import logging
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup Users'  # @ReservedAssignment
    
    def handle(self, *args, **options):
        clean_pictures()


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
                        print fname1
                        os.remove(fname1)
            
    
def update_center_usernames():
    centers = User.objects.filter(is_center=True, username__endswith='@diamondway-center.org')
    for center in centers:
        center.last_name = center.last_name.capitalize()        
        center.username = center.first_name + center.last_name
        center.save()
        
    
def remove_profile():
    centerprofile = RoleProfile.objects.get(uuid=settings.SSO_CUSTOM['DEFAULT_ADMIN_PROFILE_UUID'])
    user_list = User.objects.filter(is_center=False, role_profiles=centerprofile)
    for user in user_list:
        user.role_profiles.remove(centerprofile)
        print user
