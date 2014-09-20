# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import current_user.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('organisations', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='admin_regions',
            field=models.ManyToManyField(to='organisations.AdminRegion', null=True, verbose_name='admin regions', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='application_roles',
            field=models.ManyToManyField(to='accounts.ApplicationRole', null=True, verbose_name='application roles', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='created_by_user',
            field=models.ForeignKey(related_name=b'+', verbose_name='created by', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='last_modified_by_user',
            field=current_user.models.CurrentUserField(related_name=b'+', verbose_name='last modified by', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(to='organisations.Organisation', null=True, verbose_name='organisations', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='role_profiles',
            field=models.ManyToManyField(help_text='Organises a group of application roles that are usually assigned together.', to='accounts.RoleProfile', null=True, verbose_name='role profiles', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions'),
            preserve_default=True,
        ),
    ]
