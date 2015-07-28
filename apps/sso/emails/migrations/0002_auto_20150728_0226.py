# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='email',
            name='email',
            field=sso.models.CaseInsensitiveEmailField(unique=True, max_length=254, verbose_name='email address'),
        ),
    ]
