# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_auto_20150207_1617'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='valid_until',
            field=models.DateTimeField(null=True, verbose_name='valid until', blank=True),
            preserve_default=True,
        ),
    ]
