# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser


def clean_last_login(apps, schema_editor):
    UserModel = get_user_model()
    if issubclass(UserModel, AbstractBaseUser):
        UserModel._default_manager.filter(last_login=models.F('date_joined')).update(last_login=None)


def reverse_clean_last_login(apps, schema_editor):
    UserModel = get_user_model()
    if issubclass(UserModel, AbstractBaseUser):
        UserModel._default_manager.filter(last_login=None).update(last_login=models.F('date_joined'))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_auto_20150406_1125'),
    ]

    operations = [
        migrations.RunPython(clean_last_login, reverse_clean_last_login),
    ]
