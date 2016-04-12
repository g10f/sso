# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-03-04 16:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='last_modified',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='last modified'),
            preserve_default=False,
        ),
    ]