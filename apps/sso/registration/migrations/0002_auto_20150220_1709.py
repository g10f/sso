# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationprofile',
            name='is_access_denied',
            field=models.BooleanField(default=False, help_text='Designates if access is denied to the user.', db_index=True, verbose_name='access denied'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='registrationprofile',
            name='is_validated',
            field=models.BooleanField(default=False, help_text='Designates whether this profile was already validated by the user.', db_index=True, verbose_name='validated'),
            preserve_default=True,
        ),
    ]
