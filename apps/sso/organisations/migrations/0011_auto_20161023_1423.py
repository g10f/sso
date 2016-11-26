# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-10-23 12:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0010_auto_20161023_1411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminregion',
            name='slug',
            field=models.SlugField(blank=True, help_text='Used for URLs, auto-generated from name if blank', max_length=255, unique=True, verbose_name='Slug Name'),
        ),
    ]