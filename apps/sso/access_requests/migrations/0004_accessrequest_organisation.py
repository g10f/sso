# Generated by Django 2.1.7 on 2019-04-07 16:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0033_auto_20180729_2046'),
        ('access_requests', '0003_auto_20180618_2245'),
    ]

    operations = [
        migrations.AddField(
            model_name='accessrequest',
            name='organisation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='organisations.Organisation'),
        ),
    ]