# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0008_organisation_timezone'),
    ]

    operations = [
        migrations.CreateModel(
            name='TzWorld',
            fields=[
                ('gid', models.AutoField(serialize=False, primary_key=True)),
                ('tzid', models.CharField(max_length=30, blank=True)),
                ('geom', django.contrib.gis.db.models.fields.PolygonField(srid=4326, null=True, blank=True)),
            ],
            options={
                'db_table': 'tz_world',
            },
            bases=(models.Model,),
        ),
    ]
