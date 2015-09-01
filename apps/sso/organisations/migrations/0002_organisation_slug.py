# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='slug',
            field=models.SlugField(help_text='Used for URLs, auto-generated from name if blank', max_length=255, verbose_name='Slug Name', blank=True),
        ),
    ]
