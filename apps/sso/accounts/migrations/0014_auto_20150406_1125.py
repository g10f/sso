# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_user_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationadmin',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='applicationrole',
            name='is_inheritable_by_org_admin',
            field=models.BooleanField(default=True, help_text='Designates that the role can inherited by a organisation admin.', verbose_name='inheritable by organisation admin'),
        ),
        migrations.AlterField(
            model_name='onetimemessage',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='organisationchange',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='roleprofile',
            name='is_inheritable_by_org_admin',
            field=models.BooleanField(default=True, help_text='Designates that the role profile can inherited by a organisation admin.', verbose_name='inheritable by organisation admin'),
        ),
        migrations.AlterField(
            model_name='roleprofile',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='roleprofileadmin',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='useraddress',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='useremail',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
        migrations.AlterField(
            model_name='userphonenumber',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
    ]
