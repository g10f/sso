# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import current_user.models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistrationProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('date_registered', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date registered')),
                ('is_validated', models.BooleanField(default=False, help_text='Designates whether this profile was already validated by the user.', db_index=True, verbose_name='validated')),
                ('about_me', models.TextField(max_length=1024, verbose_name='about_me', blank=True)),
                ('known_person1_first_name', models.CharField(max_length=100, verbose_name='first name of a known person', blank=True)),
                ('known_person1_last_name', models.CharField(max_length=100, verbose_name='last name of a known person', blank=True)),
                ('known_person2_first_name', models.CharField(max_length=100, verbose_name='first name of a another known person', blank=True)),
                ('known_person2_last_name', models.CharField(max_length=100, verbose_name='last name of a another known person', blank=True)),
                ('check_back', models.BooleanField(default=False, help_text='Designates if there are open questions to check.', verbose_name='check back')),
                ('is_access_denied', models.BooleanField(default=False, help_text='Designates if access is denied to the user.', db_index=True, verbose_name='access denied')),
                ('last_modified_by_user', current_user.models.CurrentUserField(related_name='registrationprofile_last_modified_by', verbose_name='last modified by', to=settings.AUTH_USER_MODEL, null=True)),
                ('user', models.OneToOneField(verbose_name='user', to=settings.AUTH_USER_MODEL)),
                ('verified_by_user', models.ForeignKey(related_name='registrationprofile_verified_by', verbose_name='verified by', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'registration profile',
                'verbose_name_plural': 'registration profiles',
                'permissions': (('verify_users', 'Can verify users'),),
            },
        ),
    ]
