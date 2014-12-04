# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0002_auto_20141123_1936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='scopes',
            field=models.CharField(default=b'openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture')", max_length=512, verbose_name='scopes'),
            preserve_default=True,
        ),
    ]
