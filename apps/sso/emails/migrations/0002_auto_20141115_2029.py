# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailforward',
            name='primary',
            field=models.BooleanField(default=False, help_text='Designates the email address, which can only changed by users with special administration rights.', verbose_name='primary'),
            preserve_default=True,
        ),
    ]
