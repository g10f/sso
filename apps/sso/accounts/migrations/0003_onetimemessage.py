# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import sso.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20140920_1103'),
    ]

    operations = [
        migrations.CreateModel(
            name='OneTimeMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('title', models.CharField(default=b'', max_length=255, verbose_name='title')),
                ('message', models.TextField(default=b'', max_length=2048, verbose_name='message', blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
            },
            bases=(models.Model,),
        ),
    ]
