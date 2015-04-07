# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0011_auto_20150402_0012'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='name_native',
            field=models.CharField(max_length=255, verbose_name='name in native language', blank=True),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='centerid',
            field=models.IntegerField(help_text='id from the previous center DB (obsolete)', null=True, blank=True),
        ),
    ]
