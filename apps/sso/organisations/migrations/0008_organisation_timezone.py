# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0007_auto_20150228_1153'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='timezone',
            field=models.CharField(max_length=254, verbose_name='timezone', blank=True),
            preserve_default=True,
        ),
    ]
