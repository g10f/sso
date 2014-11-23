# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Designates whether this client should be treated as active. Unselect this instead of deleting clients.', verbose_name='active'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='client',
            name='scopes',
            field=models.CharField(default=b'openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'offline_access', 'address', 'phone', 'picture')", max_length=512, verbose_name='scopes'),
            preserve_default=True,
        ),
    ]
