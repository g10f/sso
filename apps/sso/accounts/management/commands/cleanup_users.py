# -*- coding: utf-8 -*-
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateformat import format
from sso.accounts.models import User
from utils.ucsv import UnicodeReader, UnicodeWriter, dic_from_csv
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup Users'  # @ReservedAssignment
    
    def handle(self, *args, **options):
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
                if not user.uuid in user_dict:
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
