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
    for basedir, dirs, files in os.walk(os.path.join(settings.MEDIA_ROOT, 'image')):
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


def cleanup():
    file_name = os.path.join(settings.BASE_DIR, '../data/dharmashop_user.csv')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="utf-8")      
        user_dict = dic_from_csv(reader)
        
    user_rows = [['uuid', 'email', 'first_name', 'last_name', 'last_login']]
    user_list = User.objects.all()
    for user in user_list:
        encoded = user.password
        algorithm = encoded.split('$')[0]
        if algorithm in ['osc_md5']:  # , 'moin_sha1'
            if user.uuid not in user_dict:
                user_rows.append([user.uuid, user.email, user.first_name, user.last_name, format(user.last_login, 'Y-m-d')])
                print user, user.last_login
                user.delete()

    file_name = os.path.join(settings.BASE_DIR, '../data/sso_deleted_user.csv')
    with open(file_name, 'wb') as csvfile1:        
        writer = UnicodeWriter(csvfile1)
        writer.writerows(user_rows)
        
    user_list = User.objects.filter(email__icontains='diamondway-center.org', is_center=False)
    for user in user_list:
        user.is_center = True
        user.save()
