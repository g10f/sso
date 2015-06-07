# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.auth.models
import django.utils.timezone
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(help_text=b'The human-readable name of this device.', max_length=255, blank=True)),
                ('confirmed', models.BooleanField(default=False, help_text=b'Is this device ready for use?')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created at')),
                ('last_used', models.DateTimeField(help_text=b'Last time this device was used?', null=True, blank=True)),
                ('order', models.IntegerField(default=0, help_text='Overwrites the alphabetic order.')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_otp_enabled', models.BooleanField(default=False, verbose_name='is otp enabled')),
            ],
        ),
        migrations.CreateModel(
            name='TOTPDevice',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='sso_auth.Device')),
                ('key', models.CharField(default=sso.auth.models.default_key, help_text=b'A hex-encoded secret key of up to 40 bytes.', max_length=80, validators=[sso.auth.models.key_validator])),
                ('step', models.PositiveSmallIntegerField(default=30, help_text=b'The time step in seconds.')),
                ('t0', models.BigIntegerField(default=0, help_text=b'The Unix time at which to begin counting steps.')),
                ('digits', models.PositiveSmallIntegerField(default=6, help_text=b'The number of digits to expect in a token.', choices=[(6, 6), (8, 8)])),
                ('tolerance', models.PositiveSmallIntegerField(default=1, help_text=b'The number of time steps in the past or future to allow.')),
                ('drift', models.SmallIntegerField(default=0, help_text=b'The number of time steps the prover is known to deviate from our clock.')),
                ('last_t', models.BigIntegerField(default=-1, help_text=b'The t value of the latest verified token. The next token must be at a higher time step.')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
            bases=('sso_auth.device',),
        ),
        migrations.CreateModel(
            name='TwilioSMSDevice',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='sso_auth.Device')),
                ('number', models.CharField(help_text=b'The mobile number to deliver tokens to.', max_length=16)),
                ('key', models.CharField(default=sso.auth.models.default_key, help_text=b'A random key used to generate tokens (hex-encoded).', max_length=40, validators=[sso.auth.models.key_validator])),
                ('last_t', models.BigIntegerField(default=-1, help_text=b'The t value of the latest verified token. The next token must be at a higher time step.')),
            ],
            options={
                'ordering': ['order', 'name'],
            },
            bases=('sso_auth.device',),
        ),
        migrations.CreateModel(
            name='U2FDevice',
            fields=[
                ('device_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='sso_auth.Device')),
                ('public_key', models.TextField()),
                ('key_handle', models.TextField()),
                ('app_id', models.TextField()),
            ],
            options={
                'ordering': ['order', 'name'],
            },
            bases=('sso_auth.device',),
        ),
        migrations.AddField(
            model_name='profile',
            name='default_device',
            field=models.ForeignKey(to='sso_auth.Device'),
        ),
        migrations.AddField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(related_name='sso_auth_profile', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='device',
            name='user',
            field=models.ForeignKey(help_text=b'The user that this device belongs to.', to=settings.AUTH_USER_MODEL),
        ),
    ]
