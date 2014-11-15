# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='center_type',
            field=models.CharField(db_index=True, max_length=2, verbose_name='center type', choices=[(b'1', 'Buddhist Center'), (b'2', 'Buddhist Group'), (b'3', 'Buddhist Retreat'), (b'4', 'Buddhist Contact'), (b'7', 'Buddhist Center & Retreat'), (b'16', 'Buddhist Group & Retreat')]),
            preserve_default=True,
        ),
    ]
