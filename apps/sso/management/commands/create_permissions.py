from optparse import make_option
from django.apps import apps

from django.db import DEFAULT_DB_ALIAS
from django.core.management.base import BaseCommand
from django.contrib.auth.management import create_permissions


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
                    help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--database', action='store', dest='database',
                    default=DEFAULT_DB_ALIAS, help='Nominates a database to create_permissions. '
                    'Defaults to the "default" database.'),
    )
    args = "[app_label]"
    help = 'reloads permissions for specified apps, or all apps if no args are specified'

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity'))
        interactive = options.get('interactive')
        database = options.get('database')

        if not args:
            app_configs = apps.get_app_configs()
        else:
            app_configs = []
            for arg in args:
                app_configs.append(apps.get_app_config(arg))

        for app_config in app_configs:
            if app_config.models_module is None:
                continue
            if verbosity >= 2:
                print("Running create_permissions for application %s" % app_config.label)

            create_permissions(app_config, verbosity, interactive, database)
