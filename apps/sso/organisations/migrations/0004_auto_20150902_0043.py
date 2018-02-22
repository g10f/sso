from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0003_auto_20150901_2351'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='slug',
            field=models.SlugField(max_length=255, blank=True, help_text='Used for URLs, auto-generated from name if blank', unique=True, verbose_name='Slug Name'),
        ),
    ]
