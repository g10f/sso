# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import smart_selects.db_fields
import django.db.models.deletion
import sso.fields
import django.contrib.gis.db.models.fields
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0001_initial'),
        ('l10n', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminRegion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this region should be treated as active. Unselect this instead of deleting the region.', verbose_name='active')),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country')),
                ('email', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='emails.Email', unique=True, verbose_name='email address')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Region',
                'verbose_name_plural': 'Regions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CountryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('email', models.ForeignKey(null=True, blank=True, to='emails.Email', unique=True, verbose_name='email address')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Country group',
                'verbose_name_plural': 'Country groups',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('notes', models.TextField(max_length=255, verbose_name='notes', blank=True)),
                ('center_type', models.CharField(db_index=True, max_length=2, verbose_name='center type', choices=[(b'1', 'Buddhist Center'), (b'2', 'Buddhist Group'), (b'3', 'Buddhist Retreat'), (b'7', 'Buddhist Center & Retreat'), (b'16', 'Buddhist Group & Retreat')])),
                ('centerid', models.IntegerField(null=True, blank=True)),
                ('founded', models.DateField(null=True, verbose_name='founded', blank=True)),
                ('coordinates_type', models.CharField(default=b'3', max_length=1, verbose_name='coordinates type', db_index=True, choices=[(b'1', 'Unknown'), (b'2', 'City/Village'), (b'3', 'Exact'), (b'4', 'Nearby')])),
                ('latitude', models.DecimalField(null=True, verbose_name='latitude', max_digits=9, decimal_places=6, blank=True)),
                ('longitude', models.DecimalField(null=True, verbose_name='longitude', max_digits=9, decimal_places=6, blank=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326, geography=True, null=True, verbose_name='longitude/latitude', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this buddhist center should be treated as active. Unselect this instead of deleting buddhist center.', verbose_name='active')),
                ('is_private', models.BooleanField(default=False, help_text='Designates whether this buddhist center data should be treated as private and only a telephone number should be displayed on public sites.', verbose_name='private')),
                ('can_publish', models.BooleanField(default=True, help_text='Designates whether this buddhist center data can be published.', verbose_name='publish')),
                ('admin_region', smart_selects.db_fields.ChainedForeignKey(verbose_name='admin region', blank=True, to='organisations.AdminRegion', null=True)),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country', null=True)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='email address', blank=True, to='emails.Email', null=True)),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['name'],
                'abstract': False,
                'verbose_name_plural': 'Buddhist Centers',
                'verbose_name': 'Buddhist Center',
                'permissions': (('access_all_organisations', 'Can access all organisations'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OrganisationAddress',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('addressee', models.CharField(max_length=80, verbose_name='addressee')),
                ('street_address', models.TextField(help_text='Full street address, with house number, street name, P.O. box, and extended street address information.', max_length=512, verbose_name='street address', blank=True)),
                ('city', models.CharField(max_length=100, verbose_name='city')),
                ('postal_code', models.CharField(max_length=30, verbose_name='postal code', blank=True)),
                ('region', models.CharField(help_text='State or region', max_length=100, verbose_name='region', blank=True)),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('address_type', models.CharField(max_length=20, verbose_name='address type', choices=[(b'meditation', 'Meditation'), (b'post', 'Post Only')])),
                ('careof', models.CharField(default=b'', max_length=80, verbose_name='care of (c/o)', blank=True)),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country')),
                ('organisation', models.ForeignKey(to='organisations.Organisation')),
                ('state', smart_selects.db_fields.ChainedForeignKey(blank=True, to='l10n.AdminArea', help_text='State or region', null=True, verbose_name='State')),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['addressee'],
                'abstract': False,
                'verbose_name_plural': 'addresses',
                'verbose_name': 'address',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OrganisationCountry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this country should be treated as active. Unselect this instead of deleting the country.', verbose_name='active')),
                ('country', models.OneToOneField(null=True, verbose_name='country', to='l10n.Country')),
                ('country_groups', models.ManyToManyField(to='organisations.CountryGroup', null=True, blank=True)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='email address', blank=True, to='emails.Email', null=True)),
            ],
            options={
                'ordering': ['country'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Country',
                'verbose_name_plural': 'Countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OrganisationPhoneNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('phone', models.CharField(max_length=30, verbose_name='phone number')),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('phone_type', models.CharField(help_text='Mobile, home, office, etc.', max_length=20, verbose_name='phone type', choices=[(b'home', 'Home'), (b'mobile', 'Mobile'), (b'mobile2', 'Mobile#2'), (b'fax', 'Fax'), (b'other', 'Other'), (b'other2', 'Other#2')])),
                ('organisation', models.ForeignKey(to='organisations.Organisation')),
            ],
            options={
                'ordering': ['-primary'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'phone number',
                'verbose_name_plural': 'phone numbers',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='organisationaddress',
            unique_together=set([('organisation', 'address_type')]),
        ),
    ]
