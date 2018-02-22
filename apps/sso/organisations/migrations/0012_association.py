# Generated by Django 1.10.5 on 2017-02-19 20:33
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0011_auto_20161023_1423'),
    ]

    operations = [
        migrations.CreateModel(
            name='Association',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(blank=True, verbose_name='homepage')),
                ('email_domain', models.CharField(blank=True, max_length=254, verbose_name='email domain')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this association should be treated as active. Unselect this instead of deleting the association.', verbose_name='active')),
                ('is_external', models.BooleanField(default=False, help_text='Designates whether this association is managed externally.', verbose_name='external')),
                ('is_selectable', models.BooleanField(default=True, help_text='Designates whether the organisations of this association can be selected by/assigned to users.', verbose_name='selectable')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Association',
                'verbose_name_plural': 'Associations',
            },
        ),
    ]
