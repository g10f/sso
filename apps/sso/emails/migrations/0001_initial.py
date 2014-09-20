# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.fields
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('email_type', models.CharField(db_index=True, max_length=20, verbose_name='email type', choices=[(b'center', 'Center'), (b'region', 'Region'), (b'country', 'Country'), (b'global_region', 'Country group'), (b'person', 'Person'), (b'group', 'Group')])),
                ('permission', models.CharField(default=b'1', max_length=20, verbose_name='access control', db_index=True, choices=[(b'1', 'Everybody'), (b'2', 'Diamondway Buddhism'), (b'3', 'VIP'), (b'4', 'VIP + Diamondway Buddhism')])),
                ('email', models.EmailField(unique=True, max_length=254, verbose_name='email address')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this email should be treated as active. Unselect this instead of deleting the email.', verbose_name='active')),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['email'],
                'abstract': False,
                'verbose_name_plural': 'Emails',
                'verbose_name': 'Email',
                'permissions': (('read_email', 'Can read mail data'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailAlias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('alias', models.EmailField(unique=True, max_length=254, verbose_name='email alias address')),
                ('email', models.ForeignKey(verbose_name='email address', to='emails.Email')),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['alias', 'email'],
                'abstract': False,
                'verbose_name_plural': 'email aliases',
                'verbose_name': 'email alias',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailForward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('forward', models.EmailField(max_length=254, verbose_name='email forwarding address')),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('email', models.ForeignKey(verbose_name='email address', to='emails.Email')),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['forward', 'email'],
                'abstract': False,
                'verbose_name_plural': 'email forwardings',
                'verbose_name': 'email forwarding',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('name', models.CharField(default=b'', max_length=255, verbose_name='name', blank=True)),
                ('homepage', models.URLField(default=b'', verbose_name='homepage', blank=True)),
                ('is_guide_email', models.BooleanField(default=False, verbose_name='guide email')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this email should be treated as active. Unselect this instead of deleting the email.', verbose_name='active')),
                ('email', models.ForeignKey(verbose_name='email address', to='emails.Email', unique=True)),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'group email',
                'verbose_name_plural': 'group emails',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupEmailManager',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('group_email', models.ForeignKey(verbose_name='group email', to='emails.GroupEmail')),
                ('manager', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'group email manager',
                'verbose_name_plural': 'group email managers',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='groupemailmanager',
            unique_together=set([('group_email', 'manager')]),
        ),
        migrations.AlterUniqueTogether(
            name='emailforward',
            unique_together=set([('email', 'forward')]),
        ),
        migrations.AlterUniqueTogether(
            name='emailalias',
            unique_together=set([('email', 'alias')]),
        ),
    ]
