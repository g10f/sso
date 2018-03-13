# Generated by Django 2.0.1 on 2018-01-12 20:42

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.query_utils


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0004_auto_20170702_1420'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupemail',
            name='email',
            field=models.OneToOneField(limit_choices_to=django.db.models.query_utils.Q(('email_type', 'group'), ('email_type', 'global_region'), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='emails.Email', verbose_name='email address'),
        ),
    ]