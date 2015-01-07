# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def code(apps, schema_editor):
    pass


def reverse_code(apps, schema_editor):
    user_model = apps.get_model("accounts", "User")
    user_email_model = apps.get_model("accounts", "UserEmail")

    for user_email in user_email_model.objects.filter(primary=True):
        user = user_email.user
        user.email = user_email.email
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20150107_1311'),
    ]

    operations = [
        migrations.RunPython(code, reverse_code=reverse_code),
        migrations.RemoveField(
            model_name='user',
            name='email',
        ),
    ]
