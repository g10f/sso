from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import current_user.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registrationprofile',
            name='last_modified_by_user',
            field=current_user.models.CurrentUserField(related_name='registrationprofile_last_modified_by', on_delete=django.db.models.deletion.SET_NULL, verbose_name='last modified by', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='registrationprofile',
            name='verified_by_user',
            field=models.ForeignKey(related_name='registrationprofile_verified_by', on_delete=django.db.models.deletion.SET_NULL, verbose_name='verified by', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
