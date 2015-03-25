# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0009_tzworld'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='coordinates_type',
            field=models.CharField(default=b'3', choices=[(b'1', 'Unknown'), (b'2', 'City/Village'), (b'3', 'Exact'), (b'4', 'Nearby')], max_length=1, blank=True, verbose_name='coordinates type', db_index=True),
            preserve_default=True,
        ),
    ]
