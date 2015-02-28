# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0006_auto_20150215_1634'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(srid=4326, geography=True, null=True, verbose_name='location', blank=True),
            preserve_default=True,
        ),
    ]
