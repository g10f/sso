from django.core.management.base import NoArgsCommand
from sso.accounts.models import User

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment
    
    def handle_noargs(self, **options):
        
        for user in User.objects.filter(is_active=True):
            print user.email
