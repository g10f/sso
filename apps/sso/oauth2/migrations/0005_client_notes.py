# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0004_auto_20150402_0012'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='notes',
            field=models.TextField(max_length=2048, verbose_name='Notes', blank=True),
        ),
    ]
