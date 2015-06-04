# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sso_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='U2FDevice',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='sso_auth.Device')),
                ('public_key', models.TextField()),
                ('key_handle', models.TextField()),
                ('app_id', models.TextField()),
            ],
            options={
                'ordering': ['order', 'name'],
            },
            bases=('sso_auth.device',),
        ),
    ]
