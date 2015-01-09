# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import UserManager

from django.db import models, migrations
import re
import sso.fields
import django.utils.timezone
from django.conf import settings
import django.core.validators


def code(apps, schema_editor):
    """
    create user_email
    """
    user_model = apps.get_model("accounts", "User")
    user_email_model = apps.get_model("accounts", "UserEmail")

    for user in user_model.objects.filter(email__isnull=False).exclude(email=''):
        if user.is_center:
            confirmed = True
        else:
            try:
                confirmed = user.registrationprofile.is_validated
            except ObjectDoesNotExist:
                confirmed = False

        email = UserManager.normalize_email(user.email)
        user_email = user_email_model(
            email=email,
            confirmed=confirmed,
            primary=True,
            user=user
        )
        user_email.save()


def reverse_code(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_onetimemessage'),
        ('registration', '0001_initial')
    ]

    operations = [
        migrations.CreateModel(
            name='UserEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', sso.fields.UUIDField(unique=True, max_length=36, editable=False, blank=True)),
                ('last_modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last modified', auto_now=True)),
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
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, max_length=30, verbose_name='username', validators=[django.core.validators.RegexValidator(re.compile(b'^[\\w.@+-]+$', 32), 'Enter a valid username.', b'invalid')]),
            preserve_default=True,
        ),
        migrations.RunPython(code, reverse_code=reverse_code),
    ]
