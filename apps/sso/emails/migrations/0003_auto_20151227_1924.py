# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-27 18:24
from __future__ import unicode_literals

from django.db import migrations
import sso.models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_auto_20150728_0226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailalias',
            name='alias',
            field=sso.models.CaseInsensitiveEmailField(max_length=254, unique=True, verbose_name='email alias address'),
        ),
        migrations.AlterField(
            model_name='emailforward',
            name='forward',
            field=sso.models.CaseInsensitiveEmailField(max_length=254, verbose_name='email forwarding address'),
        ),
    ]