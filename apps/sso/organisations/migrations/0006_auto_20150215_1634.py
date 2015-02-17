# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0005_organisation_uses_user_activation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='uses_user_activation',
            field=models.BooleanField(default=False, help_text='Designates whether this buddhist center uses the new user activation process.', verbose_name='uses activation'),
            preserve_default=True,
        ),
    ]
