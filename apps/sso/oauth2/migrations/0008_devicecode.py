# Generated manually for the RFC 8628 Device Authorization Grant

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import sso.oauth2.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('oauth2', '0007_alter_authorizationcode_state'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_code', models.CharField(max_length=100, unique=True, verbose_name='device code')),
                ('user_code', models.CharField(max_length=16, unique=True, verbose_name='user code')),
                ('scopes', models.CharField(blank=True, max_length=2047, verbose_name='scopes')),
                ('status', models.CharField(choices=[('pending', 'pending'), ('approved', 'approved'), ('denied', 'denied')],
                                            default='pending', max_length=10, verbose_name='status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('expires_at', models.DateTimeField(verbose_name='expires at')),
                ('last_polled_at', models.DateTimeField(blank=True, null=True, verbose_name='last polled at')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='oauth2.client', verbose_name='client')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                           to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'ordering': ['-created_at'],
                'get_latest_by': 'created_at',
            },
        ),
    ]
