# Generated by Django 3.1.7 on 2021-03-28 10:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('components', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='componentconfig',
            options={'get_latest_by': '-component__created_at', 'ordering': ['-component__created_at']},
        ),
    ]
