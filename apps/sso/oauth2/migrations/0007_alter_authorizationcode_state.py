# Generated by Django 5.1.6 on 2025-03-02 09:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0006_alter_authorizationcode_code_challenge_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authorizationcode',
            name='state',
            field=models.CharField(blank=True, max_length=4096, verbose_name='client state'),
        ),
    ]
