"""
A management command which deletes expired accounts (e.g.,
accounts which signed up but never validated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""

from django.core.management.base import BaseCommand

from sso.registration.models import RegistrationProfile


class Command(BaseCommand):
    help = "Remove the expired user registrations from the database"

    def handle(self, **options):
        RegistrationProfile.objects.delete_expired_users()
