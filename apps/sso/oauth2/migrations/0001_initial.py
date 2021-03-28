# Generated by Django 3.1.7 on 2021-03-28 14:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import sso.oauth2.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('sso_auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BearerToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.CharField(max_length=2048, unique=True, verbose_name='access token')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='RefreshToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=2048, unique=True, verbose_name='token')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('bearer_token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='refresh_token', to='oauth2.bearertoken', verbose_name='bearer token')),
            ],
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('last_modified', models.DateTimeField(auto_now=True, verbose_name='last modified')),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('redirect_uris', models.TextField(blank=True, verbose_name='redirect uris')),
                ('post_logout_redirect_uris', models.TextField(blank=True, verbose_name='post logout redirect uris')),
                ('default_redirect_uri', models.CharField(blank=True, max_length=2047, verbose_name='default redirect uri')),
                ('client_secret', models.CharField(blank=True, default=sso.oauth2.models.get_default_secret, max_length=2047, verbose_name='client secret')),
                ('type', models.CharField(choices=[('web', 'Web Application'), ('javascript', 'Javascript Application'), ('native', 'Native Application'), ('service', 'Service Account'), ('trusted', 'Trusted Client')], default='web', max_length=255, verbose_name='type')),
                ('scopes', models.CharField(blank=True, default='openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', 'role_profile', 'offline_access', 'address', 'phone', 'users', 'picture', 'events')", max_length=512, verbose_name='scopes')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this client should be treated as active. Unselect this instead of deleting clients.', verbose_name='active')),
                ('notes', models.TextField(blank=True, max_length=2048, verbose_name='Notes')),
                ('is_trustworthy', models.BooleanField(default=False, verbose_name='trustworthy')),
                ('force_using_pkce', models.BooleanField(default=False, help_text='Enforce Proof Key for Code Exchange <a href="https://tools.ietf.org/html/rfc7636">https://tools.ietf.org/html/rfc7636</a>', verbose_name='force using PKCE')),
                ('application', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.application', verbose_name='application')),
                ('user', models.ForeignKey(blank=True, help_text='Associated user, required for Client Credentials Grant', limit_choices_to={'is_service': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'ordering': ['name'],
                'get_latest_by': 'last_modified',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='bearertoken',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='oauth2.client', verbose_name='client'),
        ),
        migrations.AddField(
            model_name='bearertoken',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user'),
        ),
        migrations.CreateModel(
            name='AuthorizationCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=100, unique=True, verbose_name='code')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('redirect_uri', models.CharField(blank=True, max_length=2047, verbose_name='redirect uri')),
                ('is_valid', models.BooleanField(default=True, verbose_name='is valid')),
                ('state', models.CharField(blank=True, max_length=2047, verbose_name='client state')),
                ('scopes', models.CharField(blank=True, max_length=2047, verbose_name='scopes')),
                ('code_challenge', models.CharField(blank=True, max_length=128, verbose_name='code_challenge')),
                ('code_challenge_method', models.CharField(blank=True, max_length=4, verbose_name='code_challenge_method')),
                ('nonce', models.CharField(blank=True, max_length=2047, verbose_name='Nonce')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='oauth2.client', verbose_name='client')),
                ('otp_device', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='sso_auth.device')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
    ]
