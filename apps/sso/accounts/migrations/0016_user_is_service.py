# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_auto_20150402_2317'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_service',
            field=models.BooleanField(default=False, help_text='Designates that this user is representing a service account and not a person.', verbose_name='service'),
        ),
    ]
