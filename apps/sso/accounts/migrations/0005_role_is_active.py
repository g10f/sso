# Generated by Django 3.2.12 on 2022-04-10 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_application_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='is_active',
            field=models.BooleanField(db_index=True, default=True, help_text='Designates whether this Role should be treated as active. Unselect this instead of deleting Roles.', verbose_name='active'),
        ),
    ]
