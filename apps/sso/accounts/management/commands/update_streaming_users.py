from django.core.management.base import NoArgsCommand
from sso.accounts.models import UserAssociatedSystem
from sso.registration import default_username_generator
from django.utils.text import capfirst

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment
    
    def handle_noargs(self, **options):
        
        for userassociatedsystem in UserAssociatedSystem.objects.all():
            
            user = userassociatedsystem.user
            if user.first_name and user.last_name:
                user.username = default_username_generator(capfirst(user.first_name), capfirst(user.last_name))
                user.save()
