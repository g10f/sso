from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from ...models import AuthorizationCode, BearerToken


class Command(BaseCommand):
    help = "Can be run as a cronjob or directly to clean out expired tokens."

    def handle(self, **options):
        refresh_token_life_time = timezone.now() - timedelta(seconds=settings.SSO_REFRESH_TOKEN_AGE)
        five_minutes_ago = timezone.now() - timedelta(0, 300)
        # AuthorizationCode are short living, only to create a bearer token
        AuthorizationCode.objects.filter(created_at__lt=five_minutes_ago).delete()
        # BearerToken are valid for one hour, but are stored for refresh tokens.
        # Refresh Tokens are valid for REFRESH_TOKEN_LIFE_TIME days and are deleted
        # automatically when they BearerToken are deleted.
        BearerToken.objects.filter(created_at__lt=refresh_token_life_time).delete()
