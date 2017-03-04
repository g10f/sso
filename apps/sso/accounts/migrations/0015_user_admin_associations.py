# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-04 16:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0019_auto_20170303_2110'),
        ('accounts', '0014_auto_20170226_1242'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='admin_associations',
            field=models.ManyToManyField(blank=True, to='organisations.Association', verbose_name='admin associations'),
        ),
    ]
