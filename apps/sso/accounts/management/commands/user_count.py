import logging

from django.core.management.base import BaseCommand
from sso.accounts.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Countusers'  # @ReservedAssignment

    def handle(self, *args, **options):
        print(User.objects.count())
