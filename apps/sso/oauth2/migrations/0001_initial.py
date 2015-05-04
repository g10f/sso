# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sso.oauth2.models
import sso.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorizationCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=100, verbose_name='code')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('redirect_uri', models.CharField(max_length=2047, verbose_name='redirect uri', blank=True)),
                ('is_valid', models.BooleanField(default=True, verbose_name='is valid')),
                ('state', models.CharField(max_length=2047, verbose_name='client state', blank=True)),
                ('scopes', models.CharField(max_length=2047, verbose_name='scopes', blank=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='BearerToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access_token', models.CharField(unique=True, max_length=2048, verbose_name='access token')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('redirect_uris', models.TextField(verbose_name='redirect uris', blank=True)),
                ('default_redirect_uri', models.CharField(max_length=2047, verbose_name='default redirect uri', blank=True)),
                ('client_secret', models.CharField(default=sso.oauth2.models.get_default_secret, max_length=2047, verbose_name='client secret', blank=True)),
                ('type', models.CharField(default=b'web', max_length=255, verbose_name='type', choices=[(b'web', 'Web Application'), (b'javascript', 'Javascript Application'), (b'native', 'Native Application'), (b'service', 'Service Account'), (b'trusted', 'Trusted Client')])),
                ('scopes', models.CharField(default=b'openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture')", max_length=512, verbose_name='scopes')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this client should be treated as active. Unselect this instead of deleting clients.', verbose_name='active')),
                ('notes', models.TextField(max_length=2048, verbose_name='Notes', blank=True)),
                ('application', models.ForeignKey(verbose_name='application', blank=True, to='accounts.Application', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='Associated user, required for Client Credentials Grant', null=True, verbose_name='user')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
                'get_latest_by': 'last_modified',
            },
        ),
        migrations.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(unique=True, max_length=2048, verbose_name='token')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('bearer_token', models.OneToOneField(related_name='refresh_token', verbose_name='bearer token', to='oauth2.BearerToken')),
            ],
        ),
        migrations.AddField(
            model_name='bearertoken',
            name='client',
            field=models.ForeignKey(verbose_name='client', to='oauth2.Client'),
        ),
        migrations.AddField(
            model_name='bearertoken',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='authorizationcode',
            name='client',
            field=models.ForeignKey(verbose_name='client', to='oauth2.Client'),
        ),
        migrations.AddField(
            model_name='authorizationcode',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
    ]
