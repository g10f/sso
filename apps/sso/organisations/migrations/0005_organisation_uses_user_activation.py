# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0004_auto_20150207_1617'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='uses_user_activation',
            field=models.BooleanField(default=False, help_text='Designates whether this buddhist center uses the new user activation process.', verbose_name='uses validation'),
            preserve_default=True,
        ),
    ]
