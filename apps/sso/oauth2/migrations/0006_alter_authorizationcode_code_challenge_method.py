# Generated by Django 5.1.4 on 2025-01-18 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oauth2', '0005_refreshtoken_is_active_refreshtoken_last_modified_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authorizationcode',
            name='code_challenge_method',
            field=models.CharField(blank=True, max_length=5, verbose_name='code_challenge_method'),
        ),
    ]
