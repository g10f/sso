# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_auto_20151003_2301'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users', 'permissions': (('read_user', 'Can read user data'), ('access_all_users', 'Can access all users'), ('app_admin_access_all_users', 'Can access all users as App admin'))},
        ),
    ]
