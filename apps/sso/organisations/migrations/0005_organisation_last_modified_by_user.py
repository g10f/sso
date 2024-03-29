# Generated by Django 5.0 on 2023-12-28 11:46

import current_user.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0004_alter_organisation_timezone'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='last_modified_by_user',
            field=current_user.models.CurrentUserField(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='last modified by'),
        ),
    ]
