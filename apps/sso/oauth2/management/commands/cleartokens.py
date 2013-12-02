from datetime import timedelta
from django.core.management.base import NoArgsCommand
from django.utils import timezone
from ...models import AuthorizationCode, BearerToken 

class Command(NoArgsCommand):
    help = "Can be run as a cronjob or directly to clean out expired tokens."

    def handle_noargs(self, **options):
        yesterday = timezone.now() - timedelta(0, 86400)
        five_minutes_ago = timezone.now() - timedelta(0, 300)
        # AuthorizationCode are short living, only to create a bearer token
        AuthorizationCode.objects.filter(created_at__lt=five_minutes_ago).delete()
        # BearerToken are valid for one hour, but are stored for monitoring for 1 day
        BearerToken.objects.filter(created_at__lt=yesterday).delete()
