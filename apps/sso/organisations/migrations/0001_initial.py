# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import smart_selects.db_fields
import sorl.thumbnail.fields
import re
import django.contrib.gis.db.models.fields
import sso.organisations.models
import sso.fields
import django.db.models.deletion
import django.core.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminRegion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this region should be treated as active. Unselect this instead of deleting the region.', verbose_name='active')),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country')),
                ('email', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='emails.Email', verbose_name='email address')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Region',
                'verbose_name_plural': 'Regions',
            },
        ),
        migrations.CreateModel(
            name='CountryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('email', models.OneToOneField(null=True, blank=True, to='emails.Email', verbose_name='email address')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Country group',
                'verbose_name_plural': 'Country groups',
            },
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('name_native', models.CharField(max_length=255, verbose_name='name in native language', blank=True)),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('google_plus_page', sso.fields.URLFieldEx(domain=b'plus.google.com', verbose_name='Google+ page', blank=True)),
                ('facebook_page', sso.fields.URLFieldEx(domain=b'www.facebook.com', verbose_name='Facebook page', blank=True)),
                ('twitter_page', sso.fields.URLFieldEx(domain=b'twitter.com', verbose_name='Twitter page', blank=True)),
                ('notes', models.TextField(max_length=255, verbose_name='notes', blank=True)),
                ('center_type', models.CharField(db_index=True, max_length=2, verbose_name='organisation type', choices=[(b'1', 'Center'), (b'2', 'Group'), (b'3', 'Retreat'), (b'4', 'Contact'), (b'7', 'Center & Retreat'), (b'16', 'Group & Retreat')])),
                ('centerid', models.IntegerField(help_text='id from the previous center DB (obsolete)', null=True, blank=True)),
                ('founded', models.DateField(null=True, verbose_name='founded', blank=True)),
                ('coordinates_type', models.CharField(default=b'3', choices=[(b'1', 'Unknown'), (b'2', 'City/Village'), (b'3', 'Exact'), (b'4', 'Nearby')], max_length=1, blank=True, verbose_name='coordinates type', db_index=True)),
                ('latitude', models.DecimalField(null=True, verbose_name='latitude', max_digits=9, decimal_places=6, blank=True)),
                ('longitude', models.DecimalField(null=True, verbose_name='longitude', max_digits=9, decimal_places=6, blank=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326, geography=True, null=True, verbose_name='location', blank=True)),
                ('timezone', models.CharField(max_length=254, verbose_name='timezone', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this organisation should be treated as active. Unselect this instead of deleting organisation.', verbose_name='active')),
                ('is_private', models.BooleanField(default=False, help_text='Designates whether this organisation data should be treated as private and only a telephone number should be displayed on public sites.', verbose_name='private')),
                ('can_publish', models.BooleanField(default=True, help_text='Designates whether this organisation data can be published.', verbose_name='publish')),
                ('uses_user_activation', models.BooleanField(default=False, help_text='Designates whether this organisation uses the new user activation process.', verbose_name='uses activation')),
                ('admin_region', smart_selects.db_fields.ChainedForeignKey(verbose_name='admin region', blank=True, to='organisations.AdminRegion', null=True)),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country', null=True)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='email address', blank=True, to='emails.Email', null=True)),
            ],
            options={
                'get_latest_by': 'last_modified',
                'ordering': ['name'],
                'abstract': False,
                'verbose_name_plural': 'Organisations',
                'verbose_name': 'Organisation',
                'permissions': (('access_all_organisations', 'Can access all organisations'),),
            },
        ),
        migrations.CreateModel(
            name='OrganisationAddress',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('addressee', models.CharField(max_length=80, verbose_name='addressee')),
                ('street_address', models.TextField(help_text='Full street address, with house number, street name, P.O. box, and extended street address information.', max_length=512, verbose_name='street address', blank=True)),
                ('city', models.CharField(max_length=100, verbose_name='city')),
                ('city_native', models.CharField(max_length=100, verbose_name='city in native language', blank=True)),
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
        ),
        migrations.CreateModel(
            name='OrganisationCountry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('homepage', models.URLField(verbose_name='homepage', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this country should be treated as active. Unselect this instead of deleting the country.', verbose_name='active')),
                ('country', models.OneToOneField(null=True, verbose_name='country', to='l10n.Country')),
                ('country_groups', models.ManyToManyField(to='organisations.CountryGroup', blank=True)),
                ('email', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='email address', blank=True, to='emails.Email', null=True)),
            ],
            options={
                'ordering': ['country'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'Country',
                'verbose_name_plural': 'Countries',
            },
        ),
        migrations.CreateModel(
            name='OrganisationPhoneNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('phone', models.CharField(max_length=30, verbose_name='phone number', validators=[django.core.validators.RegexValidator(re.compile(b'^\\+\\d{1,3}((-?\\d+)|(\\s?\\(\\d+\\)\\s?)|\\s?\\d+){1,9}$'), 'Enter a valid phone number i.e. +49 (531) 123456', b'invalid')])),
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
        ),
        migrations.CreateModel(
            name='OrganisationPicture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('title', models.CharField(max_length=255, verbose_name='title', blank=True)),
                ('description', models.TextField(max_length=2048, verbose_name='description', blank=True)),
                ('picture', sorl.thumbnail.fields.ImageField(upload_to=sso.organisations.models.generate_filename, verbose_name='picture')),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('organisation', models.ForeignKey(to='organisations.Organisation')),
            ],
            options={
                'ordering': ['order'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'organisation picture',
                'verbose_name_plural': 'organisation pictures',
            },
        ),
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
        ),
        migrations.AlterUniqueTogether(
            name='organisationaddress',
            unique_together=set([('organisation', 'address_type')]),
        ),
    ]
