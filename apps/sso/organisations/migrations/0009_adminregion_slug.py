# Generated by Django 1.9.10 on 2016-10-23 12:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0008_organisation_neighbour_distance'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminregion',
            name='slug',
            field=models.SlugField(blank=True, help_text='Used for URLs, auto-generated from name if blank', max_length=255, verbose_name='Slug Name'),
        ),
    ]
