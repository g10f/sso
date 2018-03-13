# Generated by Django 1.10.6 on 2017-03-18 21:45
from __future__ import unicode_literals

import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_user_admin_associations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(error_messages={b'unique': 'A user with that username already exists.'}, help_text='Required. 40 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=40, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username'),
        ),
    ]