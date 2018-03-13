from django.core.exceptions import ObjectDoesNotExist

from django.core.management.base import BaseCommand
from django.utils.encoding import force_text
from sso.accounts.models import User, Application, ApplicationRole, Role  # , Interaction
from sso.organisations.models import Organisation


class Command(BaseCommand):
    DW_CONNECT_UUID = '337a17f119364bbab169ab1cfb72d192'
    args = ''
    help = 'Add app roles to users from organisation'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--test', dest='test', action='store_true',
                            help='Test mode, show affected accounts without modifying accounts.')
        parser.add_argument('-d', '--delete', dest='delete', action='store_true',
                            help='Delete the role instead of adding')
        parser.add_argument('-a', '--app', action='store', dest='app', default=self.DW_CONNECT_UUID, help='app uuid')
        parser.add_argument('-r', '--role', action='store', dest='role', default='User', help='role name')
        parser.add_argument('orgid', help='activate users from orgid.')

    def handle(self, *args, **options):
        try:
            user_role = Role.objects.get(name=options['role'])
            app = Application.objects.get(uuid=options['app'])
            app_role = ApplicationRole.objects.get(application=app, role=user_role)
            organisation = Organisation.objects.get(uuid=options['orgid'])
        except ObjectDoesNotExist as e:
            self.stdout.write(force_text(e))
            return

        self.stdout.write("#################################################################")
        if options['test']:
            self.stdout.write("Test for add_role %s for users of %s." % (app_role, organisation))
        else:
            self.stdout.write("Adding app role %s for users of %s." % (app_role, organisation))
        self.stdout.write("#################################################################")

        for user in User.objects.filter(is_active=True, is_service=False, organisations=organisation):
            if not options['test']:
                if options['delete']:
                    user.application_roles.remove(app_role)
                else:
                    user.application_roles.add(app_role)

            self.stdout.write("%s" % user)
