from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sso_auth', '0001_initial'),
        ('oauth2', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='authorizationcode',
            name='otp_device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='sso_auth.Device', null=True),
        ),
    ]
