# Generated by Django 2.1 on 2018-08-25 19:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_remove_useraddress_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(to='organisations.Organisation', verbose_name='organisations'),
        ),
    ]
