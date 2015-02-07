# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import re


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_auto_20150205_2004'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='city_native',
            field=models.CharField(max_length=100, verbose_name='city in native language', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userphonenumber',
            name='phone',
            field=models.CharField(max_length=30, verbose_name='phone number', validators=[django.core.validators.RegexValidator(re.compile(b'^\\+\\d{1,3}((-?\\d+)|(\\s?\\(\\d+\\)\\s?)|\\s?\\d+){1,9}$'), 'Enter a valid phone number i.e. +49 (531) 123456', b'invalid')]),
            preserve_default=True,
        ),
    ]
