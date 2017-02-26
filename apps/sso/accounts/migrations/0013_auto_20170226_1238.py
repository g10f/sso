# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-26 11:38
from __future__ import unicode_literals

from django.db import migrations



def update_organisation_country(apps, reverse=False):
    User = apps.get_model("accounts", "User")
    OrganisationCountry = apps.get_model("organisations", "OrganisationCountry")
    Country = apps.get_model("l10n", "Country")

    organisation_countries = dict((o.country_id, o) for o in OrganisationCountry.objects.all())
    countries = dict((o.id, o) for o in Country.objects.all())

    if reverse:
        users = User.objects.filter(admin_organisation_countries__isnull=False)
        for user in users:
            user.admin_countries = [countries[c.country_id] for c in user.admin_organisation_countries.all()]
            user.admin_organisation_countries.clear()
            user.save(update_fields=['last_modified'])
        users = User.objects.filter(app_admin_organisation_countries__isnull=False)
        for user in users:
            user.app_admin_countries = [countries[c.country_id] for c in user.app_admin_organisation_countries.all()]
            user.app_admin_organisation_countries.clear()
            user.save(update_fields=['last_modified'])
    else:
        users = User.objects.filter(admin_countries__isnull=False)
        for user in users:
            user.admin_organisation_countries = [organisation_countries[c.pk] for c in user.admin_countries.all()]
            user.save(update_fields=['last_modified'])

        users = User.objects.filter(app_admin_countries__isnull=False)
        for user in users:
            user.app_admin_organisation_countries = [organisation_countries[c.pk] for c in user.app_admin_countries.all()]
            user.save(update_fields=['last_modified'])


def forward_update_organisation_country(apps, schema_editor):
    update_organisation_country(apps)


def reverse_update_organisation_country(apps, schema_editor):
    update_organisation_country(apps, reverse=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_auto_20170226_1237'),
    ]

    operations = [
        migrations.RunPython(forward_update_organisation_country, reverse_code=reverse_update_organisation_country),
    ]
