# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_auto_20141115_2029'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='emailalias',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='emailforward',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='groupemail',
            name='email',
            field=models.OneToOneField(verbose_name='email address', to='emails.Email'),
        ),
        migrations.AlterField(
            model_name='groupemail',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
    ]
