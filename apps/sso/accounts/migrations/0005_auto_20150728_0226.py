# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_application_redirect_to_after_first_login'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useremail',
            name='email',
            field=sso.models.CaseInsensitiveEmailField(unique=True, max_length=254, verbose_name='email address'),
        ),
    ]
