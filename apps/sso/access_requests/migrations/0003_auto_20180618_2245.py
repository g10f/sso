# Generated by Django 2.0.6 on 2018-06-18 20:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('access_requests', '0002_accessrequest_application'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accessrequest',
            name='application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.Application', verbose_name='application'),
        ),
    ]
