# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20150524_1410'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='redirect_to_after_first_login',
            field=models.BooleanField(default=False, help_text='Designates whether the user should redirected to this app after the first login.', verbose_name='redirect to after first login'),
        ),
    ]
