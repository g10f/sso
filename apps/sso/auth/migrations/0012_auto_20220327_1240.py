# Generated by Django 3.2.12 on 2022-03-27 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sso_auth', '0011_alter_profile_default_device_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='totpdevice',
            name='drift',
        ),
        migrations.RemoveField(
            model_name='totpdevice',
            name='t0',
        ),
        migrations.AlterField(
            model_name='profile',
            name='default_device_id',
            field=models.IntegerField(choices=[('U2FDevice', 1), ('TOTPDevice', 2)], default=None, null=True),
        ),
    ]