from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from sso.accounts.models import UserEmail
from optparse import make_option
from django.utils.timezone import now
from datetime import timedelta


class Command(BaseCommand):
    args = ''
    help = 'Cleans unconfirmed non primary email addresses.'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true', dest='delete', default=False, help='Delete unconfirmed non primary email addresses')
        parser.add_argument('-m', '--minutes', action='store', dest='minutes', type=int, default=0, help='minutes since last modified')

    def handle(self, *args, **options):

        last_modified_lt = now() - timedelta(minutes=options['minutes'])
        for user_email in UserEmail.objects.filter(confirmed=False, primary=False, last_modified__lt=last_modified_lt):
            if user_email.user.useremail_set.all().count() > 1:
                if options['delete']:
                    self.stdout.write("deleting %s" % force_str(user_email))
                    user_email.delete()
                else:
                    self.stdout.write("unconfirmed non primary email %s" % force_str(user_email))
            else:
                self.stdout.write("making %s as primary" % force_str(user_email))
                user_email.primary = True
                user_email.save()
