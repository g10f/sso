# Generated by Django 1.11.3 on 2017-07-02 12:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0004_auto_20170319_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='scopes',
            field=models.CharField(blank=True, default='openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture')", max_length=512, verbose_name='scopes'),
        ),
        migrations.AlterField(
            model_name='client',
            name='type',
            field=models.CharField(choices=[('web', 'Web Application'), ('javascript', 'Javascript Application'), ('native', 'Native Application'), ('service', 'Service Account'), ('trusted', 'Trusted Client')], default='web', max_length=255, verbose_name='type'),
        ),
    ]
