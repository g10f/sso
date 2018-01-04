# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-04 10:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_auto_20170702_1420'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roleprofile',
            name='application_roles',
            field=models.ManyToManyField(blank=True, help_text='Associates a group of application roles that are usually assigned together.', to='accounts.ApplicationRole'),
        ),
    ]
