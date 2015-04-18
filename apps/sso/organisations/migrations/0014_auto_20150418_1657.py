# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0013_organisationpicture'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='organisation',
            options={'ordering': ['name'], 'get_latest_by': 'last_modified', 'verbose_name': 'Organisation', 'verbose_name_plural': 'Organisations', 'permissions': (('access_all_organisations', 'Can access all organisations'),)},
        ),
        migrations.AlterField(
            model_name='organisation',
            name='can_publish',
            field=models.BooleanField(default=True, help_text='Designates whether this organisation data can be published.', verbose_name='publish'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='center_type',
            field=models.CharField(db_index=True, max_length=2, verbose_name='organisation type', choices=[(b'1', 'Center'), (b'2', 'Group'), (b'3', 'Retreat'), (b'4', 'Contact'), (b'7', 'Center & Retreat'), (b'16', 'Group & Retreat')]),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Designates whether this organisation should be treated as active. Unselect this instead of deleting organisation.', verbose_name='active'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='is_private',
            field=models.BooleanField(default=False, help_text='Designates whether this organisation data should be treated as private and only a telephone number should be displayed on public sites.', verbose_name='private'),
        ),
        migrations.AlterField(
            model_name='organisation',
            name='uses_user_activation',
            field=models.BooleanField(default=False, help_text='Designates whether this organisation uses the new user activation process.', verbose_name='uses activation'),
        ),
    ]
