# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-02 12:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0027_auto_20170701_2126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminregion',
            name='organisation_country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisations.OrganisationCountry', verbose_name='country'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='center_type',
            field=models.CharField(choices=[('g', 'Group')], db_index=True, max_length=2, verbose_name='organisation type'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='organisation_country',
            field=smart_selects.db_fields.ChainedForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organisations.OrganisationCountry', verbose_name='country'),
        ),
    ]
