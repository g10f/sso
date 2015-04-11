# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import sso.organisations.models
import sso.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0012_auto_20150406_2244'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationPicture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('title', models.CharField(max_length=255, verbose_name='title', blank=True)),
                ('description', models.TextField(max_length=2048, verbose_name='description', blank=True)),
                ('picture', sorl.thumbnail.fields.ImageField(upload_to=sso.organisations.models.generate_filename, verbose_name='picture')),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('organisation', models.ForeignKey(to='organisations.Organisation')),
            ],
            options={
                'ordering': ['order'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'organisation picture',
                'verbose_name_plural': 'organisation pictures',
            },
        ),
    ]
