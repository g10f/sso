from optparse import make_option
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from sso.accounts.email import send_account_expires_info
from sso.accounts.models import User  # , Interaction
from django.utils.timezone import now


class Command(BaseCommand):
    args = ''
    help = 'Sends email warnings to users where the account shortly expires.'

    option_list = BaseCommand.option_list + (
        make_option('-t', '--test', action='store_true', dest='test', default=False, help='Test mode, show accounts without sending an email'),
        make_option('-d', '--days', action='store', dest='days', type="int", default=0, help='days till account expires'),
    )

    def handle(self, *args, **options):
        now_plus_x_days = now() + timedelta(days=options['days'])
        subject = 'expiration warning %s days' % options['days']
        if not settings.SSO_VALIDATION_PERIOD_IS_ACTIVE:
            self.stdout.write("expiring of user validation is not active. Set SSO_VALIDATION_PERIOD_IS_ACTIVE=True in the settings.")
        else:
            for user in User.objects.filter(is_active=True,
                                            organisations__uses_user_activation=True,
                                            valid_until__year=now_plus_x_days.year,
                                            valid_until__month=now_plus_x_days.month,
                                            valid_until__day=now_plus_x_days.day):
                if not options['test']:
                    send_account_expires_info(user, base_url=settings.SSO_BASE_URL)

                self.stdout.write(u"%s: %s" % (user, user.valid_until - now()))
