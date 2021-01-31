from django.core.management.base import BaseCommand
from ...keys import create_key


class Command(BaseCommand):
    help = "Can be run as a cronjob or directly to rotate the signing keys."

    def handle(self, **options):
        for algorithm in ['RS256', 'HS256']:
            create_key(algorithm)
