# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.fields
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_remove_user_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationAdmin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('admin', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('application', models.ForeignKey(verbose_name='application', to='accounts.Application')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'application admin',
                'verbose_name_plural': 'application admins',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RoleProfileAdmin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('admin', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('role_profile', models.ForeignKey(verbose_name='role profile', to='accounts.RoleProfile')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'role profile admin',
                'verbose_name_plural': 'role profile admins',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='roleprofileadmin',
            unique_together=set([('role_profile', 'admin')]),
        ),
        migrations.AlterUniqueTogether(
            name='applicationadmin',
            unique_together=set([('application', 'admin')]),
        ),
    ]
