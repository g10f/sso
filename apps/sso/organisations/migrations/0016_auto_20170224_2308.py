# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-24 22:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0015_auto_20170219_2224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminregion',
            name='country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='l10n.Country', verbose_name='country'),
        ),
    ]
