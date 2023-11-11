# Generated by Django 4.2.7 on 2023-11-05 20:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0004_alter_organisation_timezone'),
        ('accounts', '0008_alter_user_organisations'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='applicationrole',
            options={'ordering': ['application', 'role'], 'permissions': (('access_all_application_roles', 'Can access all applications roles'),), 'verbose_name': 'application role', 'verbose_name_plural': 'application roles'},
        ),
        migrations.AlterField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(through='accounts.Membership', to='organisations.organisation', verbose_name='organisations'),
        ),
    ]
