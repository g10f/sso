# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0010_auto_20150325_0839'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminregion',
            name='email',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='emails.Email', verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='adminregion',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='countrygroup',
            name='email',
            field=models.OneToOneField(null=True, blank=True, to='emails.Email', verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='countrygroup',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='organisationaddress',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='organisationcountry',
            name='country_groups',
            field=models.ManyToManyField(to='organisations.CountryGroup', blank=True),
        ),
        migrations.AlterField(
            model_name='organisationcountry',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='organisationphonenumber',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
    ]
