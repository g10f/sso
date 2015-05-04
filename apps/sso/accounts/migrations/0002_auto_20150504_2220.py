# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import current_user.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
        ('organisations', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisationchange',
            name='organisation',
            field=models.ForeignKey(to='organisations.Organisation'),
        ),
        migrations.AddField(
            model_name='organisationchange',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='onetimemessage',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='applicationrole',
            name='application',
            field=models.ForeignKey(to='accounts.Application'),
        ),
        migrations.AddField(
            model_name='applicationrole',
            name='role',
            field=models.ForeignKey(to='accounts.Role'),
        ),
        migrations.AddField(
            model_name='applicationadmin',
            name='admin',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='applicationadmin',
            name='application',
            field=models.ForeignKey(verbose_name='application', to='accounts.Application'),
        ),
        migrations.AddField(
            model_name='user',
            name='admin_countries',
            field=models.ManyToManyField(to='l10n.Country', verbose_name='admin countries', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='admin_regions',
            field=models.ManyToManyField(to='organisations.AdminRegion', verbose_name='admin regions', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='application_roles',
            field=models.ManyToManyField(to='accounts.ApplicationRole', verbose_name='application roles', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='created_by_user',
            field=models.ForeignKey(related_name='+', verbose_name='created by', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='user',
            name='last_modified_by_user',
            field=current_user.models.CurrentUserField(related_name='+', verbose_name='last modified by', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(to='organisations.Organisation', verbose_name='organisations', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='role_profiles',
            field=models.ManyToManyField(help_text='Organises a group of application roles that are usually assigned together.', to='accounts.RoleProfile', verbose_name='role profiles', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions'),
        ),
        migrations.AlterUniqueTogether(
            name='userassociatedsystem',
            unique_together=set([('application', 'userid')]),
        ),
        migrations.AlterUniqueTogether(
            name='useraddress',
            unique_together=set([('user', 'address_type')]),
        ),
        migrations.AlterUniqueTogether(
            name='roleprofileadmin',
            unique_together=set([('role_profile', 'admin')]),
        ),
        migrations.AlterUniqueTogether(
            name='applicationrole',
            unique_together=set([('application', 'role')]),
        ),
        migrations.AlterUniqueTogether(
            name='applicationadmin',
            unique_together=set([('application', 'admin')]),
        ),
    ]
