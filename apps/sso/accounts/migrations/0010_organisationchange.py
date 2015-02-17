# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import sso.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0006_auto_20150215_1634'),
        ('accounts', '0009_user_valid_until'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisationChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('reason', models.TextField(max_length=2048, verbose_name='reason')),
                ('organisation', models.ForeignKey(to='organisations.Organisation')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'organisation change',
                'verbose_name_plural': 'organisation change',
            },
            bases=(models.Model,),
        ),
    ]
