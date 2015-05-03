# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import smart_selects.db_fields
import re
import django.utils.timezone
from django.conf import settings
import sso.accounts.models
import django.core.validators
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, max_length=30, verbose_name='username', validators=[django.core.validators.RegexValidator(re.compile(b'^[\\w.@+-]+$', 32), 'Enter a valid username.', b'invalid')])),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', db_index=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('is_center', models.BooleanField(default=False, help_text='Designates that this user is representing a organisation and not a private person.', verbose_name='organisation')),
                ('is_service', models.BooleanField(default=False, help_text='Designates that this user is representing a service account and not a person.', verbose_name='service')),
                ('is_subscriber', models.BooleanField(default=False, help_text='Designates whether this user is a newsletter subscriber.', verbose_name='subscriber')),
                ('picture', sorl.thumbnail.fields.ImageField(upload_to=sso.accounts.models.generate_filename, verbose_name='picture', blank=True)),
                ('notes', models.TextField(max_length=1024, verbose_name='Notes', blank=True)),
                ('gender', models.CharField(blank=True, max_length=255, verbose_name='gender', choices=[(b'm', 'male'), (b'f', 'female')])),
                ('dob', models.DateField(null=True, verbose_name='date of birth', blank=True)),
                ('homepage', models.URLField(max_length=512, verbose_name='homepage', blank=True)),
                ('language', models.CharField(blank=True, max_length=254, verbose_name='language', choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')])),
                ('timezone', models.CharField(max_length=254, verbose_name='timezone', blank=True)),
                ('valid_until', models.DateTimeField(null=True, verbose_name='valid until', blank=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'permissions': (('read_user', 'Can read user data'), ('access_all_users', 'Can access all users')),
            },
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('title', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=2047, blank=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('global_navigation', models.BooleanField(default=True, help_text='Designates whether this application should be shown in the global navigation bar.', verbose_name='global navigation')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this application should be provided.', verbose_name='active')),
            ],
            options={
                'ordering': ['order', 'title'],
                'verbose_name': 'application',
                'verbose_name_plural': 'applications',
            },
        ),
        migrations.CreateModel(
            name='ApplicationAdmin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'application admin',
                'verbose_name_plural': 'application admins',
            },
        ),
        migrations.CreateModel(
            name='ApplicationRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_inheritable_by_org_admin', models.BooleanField(default=True, help_text='Designates that the role can inherited by a organisation admin.', verbose_name='inheritable by organisation admin')),
                ('is_inheritable_by_global_admin', models.BooleanField(default=True, help_text='Designates that the role can inherited by a global admin.', verbose_name='inheritable by global admin')),
                ('is_organisation_related', models.BooleanField(default=False, help_text='Designates that the role will be deleted in case of a change of the organisation.', verbose_name='organisation related')),
            ],
            options={
                'ordering': ['application', 'role'],
                'verbose_name': 'application role',
                'verbose_name_plural': 'application roles',
            },
        ),
        migrations.CreateModel(
            name='OneTimeMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('title', models.CharField(default=b'', max_length=255, verbose_name='title')),
                ('message', models.TextField(default=b'', max_length=2048, verbose_name='message', blank=True)),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'one time message',
                'verbose_name_plural': 'one time messages',
            },
        ),
        migrations.CreateModel(
            name='OrganisationChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('reason', models.TextField(max_length=2048, verbose_name='reason')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'organisation change',
                'verbose_name_plural': 'organisation change',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, verbose_name='name')),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('group', models.ForeignKey(blank=True, to='auth.Group', help_text='Associated group for SSO internal permission management.', null=True)),
            ],
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'role',
                'verbose_name_plural': 'roles',
            },
        ),
        migrations.CreateModel(
            name='RoleProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('is_inheritable_by_org_admin', models.BooleanField(default=True, help_text='Designates that the role profile can inherited by a organisation admin.', verbose_name='inheritable by organisation admin')),
                ('is_inheritable_by_global_admin', models.BooleanField(default=True, help_text='Designates that the role profile can inherited by a global admin.', verbose_name='inheritable by global admin')),
                ('application_roles', models.ManyToManyField(help_text='Associates a group of application roles that are usually assigned together.', to='accounts.ApplicationRole')),
            ],
            options={
                'ordering': ['order', 'name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'role profile',
                'verbose_name_plural': 'role profiles',
            },
        ),
        migrations.CreateModel(
            name='RoleProfileAdmin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('admin', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('role_profile', models.ForeignKey(verbose_name='role profile', to='accounts.RoleProfile')),
            ],
            options={
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'role profile admin',
                'verbose_name_plural': 'role profile admins',
            },
        ),
        migrations.CreateModel(
            name='UserAddress',
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
                ('address_type', models.CharField(max_length=20, verbose_name='address type', choices=[(b'home', 'Home'), (b'work', 'Business'), (b'other', 'Other')])),
                ('country', models.ForeignKey(verbose_name='country', to='l10n.Country')),
                ('state', smart_selects.db_fields.ChainedForeignKey(blank=True, to='l10n.AdminArea', help_text='State or region', null=True, verbose_name='State')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
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
            name='UserAssociatedSystem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('userid', models.CharField(max_length=255)),
                ('application', models.ForeignKey(to='accounts.Application')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'associated system',
                'verbose_name_plural': 'associated systems',
            },
        ),
        migrations.CreateModel(
            name='UserEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('email', models.EmailField(unique=True, max_length=254, verbose_name='email address')),
                ('confirmed', models.BooleanField(default=False, verbose_name='confirmed')),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['email'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'email address',
                'verbose_name_plural': 'email addresses',
            },
        ),
        migrations.CreateModel(
            name='UserPhoneNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('phone', models.CharField(max_length=30, verbose_name='phone number', validators=[django.core.validators.RegexValidator(re.compile(b'^\\+\\d{1,3}((-?\\d+)|(\\s?\\(\\d+\\)\\s?)|\\s?\\d+){1,9}$'), 'Enter a valid phone number i.e. +49 (531) 123456', b'invalid')])),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('phone_type', models.CharField(help_text='Mobile, home, office, etc.', max_length=20, verbose_name='phone type', choices=[(b'home', 'Home'), (b'mobile', 'Mobile'), (b'work', 'Business'), (b'fax', 'Fax'), (b'pager', 'Pager'), (b'other', 'Other')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-primary'],
                'abstract': False,
                'get_latest_by': 'last_modified',
                'verbose_name': 'phone number',
                'verbose_name_plural': 'phone numbers',
            },
        ),
    ]
