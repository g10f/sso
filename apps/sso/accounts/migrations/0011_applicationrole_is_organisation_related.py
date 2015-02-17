# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_organisationchange'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationrole',
            name='is_organisation_related',
            field=models.BooleanField(default=False, help_text='Designates that the role will be deleted in case of a change of the organisation.', verbose_name='organisation related'),
            preserve_default=True,
        ),
    ]
