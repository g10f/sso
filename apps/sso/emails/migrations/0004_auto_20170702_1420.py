# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-02 12:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0003_auto_20151227_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='email_type',
            field=models.CharField(choices=[('center', 'Center'), ('region', 'Region'), ('country', 'Country'), ('global_region', 'Country group'), ('person', 'Person'), ('group', 'Group')], db_index=True, max_length=20, verbose_name='email type'),
        ),
        migrations.AlterField(
            model_name='email',
            name='permission',
            field=models.CharField(choices=[('1', 'Everybody'), ('2', 'Diamondway Buddhism'), ('3', 'VIP'), ('4', 'VIP + Diamondway Buddhism')], db_index=True, default='1', max_length=20, verbose_name='access control'),
        ),
        migrations.AlterField(
            model_name='groupemail',
            name='homepage',
            field=models.URLField(blank=True, default='', verbose_name='homepage'),
        ),
        migrations.AlterField(
            model_name='groupemail',
            name='name',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='name'),
        ),
    ]
