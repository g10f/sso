# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryCallingCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('calling_code', models.PositiveIntegerField(unique=True, verbose_name='calling code')),
                ('country', models.ForeignKey(to='l10n.Country')),
            ],
            options={
                'ordering': ('country__iso2_code',),
                'verbose_name': 'country calling code',
                'verbose_name_plural': 'country calling codes',
            },
            bases=(models.Model,),
        ),
    ]
