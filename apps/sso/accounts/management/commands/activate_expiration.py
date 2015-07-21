import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from sso.accounts.models import User  # , Interaction
from django.utils.timezone import now
from sso.organisations.models import Organisation


class Command(BaseCommand):
    args = ''
    help = 'Activates the user expiration for accounts of centers with activated expiration.'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--test', dest='test', action='store_true', help='Test mode, show affected accounts without activating expiration.')
        parser.add_argument('-d', '--days', action='store', dest='days', type=int, default=30, help='days till the accounts expire'),
        parser.add_argument('-f', '--from', action='store', dest='from', type=int, default=7, help='days from when the accounts expires'),
        parser.add_argument('-o', '--orgid', action='store', dest='orgid', required=True, help='activate users from orgid.'),

    def handle(self, *args, **options):
        if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
            self.stdout.write("expiring of user validation is not active. Set SSO_VALIDATION_PERIOD_IS_ACTIVE=True in the settings.")
            return

        if options['days'] <= options['from']:
            self.stdout.write("days till must be grater the from.")
            return

        organisation = Organisation.objects.get(uuid=options['orgid'])
        if not organisation.uses_user_activation:
            self.stdout.write("%s is not activated for the new expiration process." % organisation)
            return

        self.stdout.write("#################################################################")
        if options['test']:
            self.stdout.write("Test for activating expiration for users of %s." % organisation)
        else:
            self.stdout.write("Activating expiration for users of %s." % organisation)
        self.stdout.write("#################################################################")

        random.seed()
        for user in User.objects.filter(is_active=True, is_service=False, is_center=False,
                                        organisations__uses_user_activation=True,
                                        organisations=organisation,
                                        valid_until__isnull=True):
            valid_until = now() + timedelta(days=random.randint(options['from'], options['days']))
            if not options['test']:
                user.valid_until = valid_until
                user.save(update_fields=['valid_until'])

            self.stdout.write(u"%s: %s" % (user, valid_until))
