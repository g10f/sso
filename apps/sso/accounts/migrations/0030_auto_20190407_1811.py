# Generated by Django 2.1.7 on 2019-04-07 16:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0029_membership'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='membership',
            options={'verbose_name': 'organisation membership', 'verbose_name_plural': 'organisation memberships'},
        ),
    ]