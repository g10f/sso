# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_auto_20150201_2056'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='onetimemessage',
            options={'get_latest_by': 'last_modified', 'verbose_name': 'one time message', 'verbose_name_plural': 'one time messages'},
        ),
        migrations.AlterModelOptions(
            name='role',
            options={'ordering': ['order', 'name'], 'verbose_name': 'role', 'verbose_name_plural': 'roles'},
        ),
    ]
