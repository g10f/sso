# Generated by Django 2.0.2 on 2018-02-24 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_auto_20180224_2002'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationchange',
            name='message',
            field=models.TextField(blank=True, help_text='Message for the organisation administrator.', max_length=2048, verbose_name='message'),
        ),
    ]
