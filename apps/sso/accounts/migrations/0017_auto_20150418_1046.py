# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_user_is_service'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='is_center',
            field=models.BooleanField(default=False, help_text='Designates that this user is representing a organisation and not a private person.', verbose_name='organisation'),
        ),
    ]
