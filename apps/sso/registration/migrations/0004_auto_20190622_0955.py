# Generated by Django 2.2.2 on 2019-06-22 07:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0003_registrationprofile_comment'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='registrationprofile',
            options={'verbose_name': 'registration profile', 'verbose_name_plural': 'registration profiles'},
        ),
        migrations.RemoveField(
            model_name='registrationprofile',
            name='verified_by_user',
        ),
    ]
