# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0003_auto_20141205_0002'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='last modified'),
        ),
    ]
