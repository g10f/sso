# Generated by Django 2.2.7 on 2019-11-16 20:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0013_authorizationcode_nonce'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='scopes',
            field=models.CharField(blank=True, default='openid profile email', help_text="Allowed space-delimited access token scopes ('openid', 'profile', 'email', 'role', 'offline_access', 'address', 'phone', 'users', 'picture', 'events')", max_length=512, verbose_name='scopes'),
        ),
    ]