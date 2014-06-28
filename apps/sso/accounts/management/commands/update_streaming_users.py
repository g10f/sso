import os
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.utils.text import capfirst

from sso.accounts.models import UserAssociatedSystem, User
from sso.registration import default_username_generator
from utils.ucsv import UnicodeReader, dic_from_csv

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment
    
    def handle_noargs(self, **options):
        import_names()
        
def import_names():
    file_name = os.path.join(settings.BASE_DIR, '../data/all_active_streaming_users_names.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="ISO-8859-1", delimiter=';')      
        user_dict = dic_from_csv(reader)
    
    # user_rows = [['email', 'last_name', 'first_name']]
    for (email, row) in user_dict.items():
        try:
            user = User.objects.get(email__iexact=email, first_name='', last_name='')
            user.first_name = row['first_name']
            user.last_name = row['last_name']
            user.username = default_username_generator(capfirst(row['first_name']), capfirst(row['last_name']))
            user.save()
        except ObjectDoesNotExist:
            pass
            

def update_username():
    for userassociatedsystem in UserAssociatedSystem.objects.all():
        
        user = userassociatedsystem.user
        if user.first_name and user.last_name:
            user.username = default_username_generator(capfirst(user.first_name), capfirst(user.last_name))
            user.save()
