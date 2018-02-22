from __future__ import unicode_literals

from django.db import models, migrations
import current_user.models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20150504_2220'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='created_by_user',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='created by', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_modified_by_user',
            field=current_user.models.CurrentUserField(related_name='+', on_delete=django.db.models.deletion.SET_NULL, verbose_name='last modified by', to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
