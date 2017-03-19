# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
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
        ),
        migrations.CreateModel(
            name='EmailAlias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('alias', models.EmailField(unique=True, max_length=254, verbose_name='email alias address')),
                ('email', models.ForeignKey(verbose_name='email address', to='emails.Email', on_delete=models.CASCADE)),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['alias', 'email'],
                'abstract': False,
                'verbose_name_plural': 'email aliases',
                'verbose_name': 'email alias',
            },
        ),
        migrations.CreateModel(
            name='EmailForward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('forward', models.EmailField(max_length=254, verbose_name='email forwarding address')),
                ('primary', models.BooleanField(default=False, help_text='Designates the email address, which can only changed by users with special administration rights.', verbose_name='primary')),
                ('email', models.ForeignKey(verbose_name='email address', to='emails.Email', on_delete=models.CASCADE)),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['forward', 'email'],
                'abstract': False,
                'verbose_name_plural': 'email forwardings',
                'verbose_name': 'email forwarding',
            },
        ),
        migrations.CreateModel(
            name='GroupEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(default=b'', max_length=255, verbose_name='name', blank=True)),
                ('homepage', models.URLField(default=b'', verbose_name='homepage', blank=True)),
                ('is_guide_email', models.BooleanField(default=False, verbose_name='guide email')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this email should be treated as active. Unselect this instead of deleting the email.', verbose_name='active')),
                ('email', models.OneToOneField(verbose_name='email address', to='emails.Email', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'group email',
                'verbose_name_plural': 'group emails',
            },
        ),
        migrations.CreateModel(
            name='GroupEmailManager',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('group_email', models.ForeignKey(verbose_name='group email', to='emails.GroupEmail', on_delete=models.CASCADE)),
                ('manager', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'group email manager',
                'verbose_name_plural': 'group email managers',
            },
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
