# Generated by Django 2.1 on 2018-08-25 19:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_to_membership(apps, reverse=False):
    User = apps.get_model("accounts", "User")
    Membership = apps.get_model("accounts", "Membership")

    if reverse:
        for membership in Membership.objects.all():
            User.organisations.through.objects.create(user=membership.user, organisation=membership.organisation)
    else:
        for membership in User.organisations.through.objects.all():
            Membership.objects.create(user=membership.user, organisation=membership.organisation)


def forward_migrate_to_membership(apps, schema_editor):
    migrate_to_membership(apps)


def reverse_migrate_to_membership(apps, schema_editor):
    migrate_to_membership(apps, reverse=True)


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0033_auto_20180729_2046'),
        ('accounts', '0028_auto_20180825_2102'),
    ]

    operations = [
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('primary', models.BooleanField(default=False, verbose_name='primary')),
                ('organisation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='organisations.Organisation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='membership',
            unique_together={('user', 'organisation')},
        ),
        migrations.RunPython(forward_migrate_to_membership, reverse_code=reverse_migrate_to_membership),
        migrations.RemoveField(
            model_name='user',
            name='organisations',
        ),
        migrations.AddField(
            model_name='user',
            name='organisations',
            field=models.ManyToManyField(through='accounts.Membership', to='organisations.Organisation',
                                         verbose_name='organisations'),
        ),
    ]
