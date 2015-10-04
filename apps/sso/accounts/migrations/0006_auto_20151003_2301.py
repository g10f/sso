# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
        ('organisations', '0004_auto_20150902_0043'),
        ('accounts', '0005_auto_20150728_0226'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='app_admin_countries',
            field=models.ManyToManyField(related_name='app_admin_user', verbose_name='app admin countries', to='l10n.Country', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='app_admin_regions',
            field=models.ManyToManyField(related_name='app_admin_user', verbose_name='app admin regions', to='organisations.AdminRegion', blank=True),
        ),
    ]
