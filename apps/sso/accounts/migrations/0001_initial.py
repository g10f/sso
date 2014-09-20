# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import smart_selects.db_fields
import sso.fields
import django.utils.timezone
from django.conf import settings
import sso.accounts.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('l10n', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, max_length=30, verbose_name='username', validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username.', 'invalid')])),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('is_center', models.BooleanField(default=False, help_text='Designates that this user is representing a center and not a private person.', verbose_name='center')),
                ('is_subscriber', models.BooleanField(default=False, help_text='Designates whether this user is a DWBN News subscriber.', verbose_name='subscriber')),
                ('picture', sorl.thumbnail.fields.ImageField(upload_to=sso.accounts.models.generate_filename, verbose_name='picture', blank=True)),
                ('notes', models.TextField(max_length=1024, verbose_name='Notes', blank=True)),
                ('gender', models.CharField(blank=True, max_length=255, verbose_name='gender', choices=[(b'm', 'male'), (b'f', 'female')])),
                ('dob', models.DateField(null=True, verbose_name='date of birth', blank=True)),
                ('homepage', models.URLField(max_length=512, verbose_name='homepage', blank=True)),
                ('language', models.CharField(blank=True, max_length=254, verbose_name='language', choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')])),
                ('admin_countries', models.ManyToManyField(to='l10n.Country', null=True, verbose_name='admin countries', blank=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'permissions': (('read_user', 'Can read user data'), ('access_all_users', 'Can access all users')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('title', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=2047, blank=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('global_navigation', models.BooleanField(default=True, help_text='Designates whether this application should be shown in the global navigation bar.', verbose_name='global navigation')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this application should be provided.', verbose_name='active')),
            ],
            options={
                'ordering': ['order', 'title'],
                'verbose_name': 'application',
                'verbose_name_plural': 'applications',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ApplicationRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_inheritable_by_org_admin', models.BooleanField(default=True, help_text='Designates that the role can inherited by a organisation admin.', verbose_name='inheritable by center admin')),
                ('is_inheritable_by_global_admin', models.BooleanField(default=True, help_text='Designates that the role can inherited by a global admin.', verbose_name='inheritable by global admin')),
                ('application', models.ForeignKey(to='accounts.Application')),
            ],
            options={
                'ordering': ['application', 'role'],
                'verbose_name': 'application role',
                'verbose_name_plural': 'application roles',
            },
            bases=(models.Model,),
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
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RoleProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
                ('is_inheritable_by_org_admin', models.BooleanField(default=True, help_text='Designates that the role profile can inherited by a organisation admin.', verbose_name='inheritable by center admin')),
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
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserAddress',
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
            bases=(models.Model,),
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
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserPhoneNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
                ('phone', models.CharField(max_length=30, verbose_name='phone number')),
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
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userassociatedsystem',
            unique_together=set([('application', 'userid')]),
        ),
        migrations.AlterUniqueTogether(
            name='useraddress',
            unique_together=set([('user', 'address_type')]),
        ),
        migrations.AddField(
            model_name='applicationrole',
            name='role',
            field=models.ForeignKey(to='accounts.Role'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='applicationrole',
            unique_together=set([('application', 'role')]),
        ),
    ]
