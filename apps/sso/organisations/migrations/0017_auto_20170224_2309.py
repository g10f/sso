# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-24 22:09
from __future__ import unicode_literals

from django.db import migrations


def update_organisation_country(apps, reverse=False):
    Organisation = apps.get_model("organisations", "Organisation")
    AdminRegion = apps.get_model("organisations", "AdminRegion")
    OrganisationCountry = apps.get_model("organisations", "OrganisationCountry")
    Country = apps.get_model("l10n", "Country")

    organisation_countries = dict((o.country_id, o) for o in OrganisationCountry.objects.all())
    countries = dict((o.id, o) for o in Country.objects.all())

    if reverse:
        organisations = Organisation.objects.filter(organisation_country__isnull=False)
        for organisation in organisations:
            organisation.country = countries[organisation.organisation_country.country_id]
            organisation.organisation_country = None
            organisation.save(update_fields=['organisation_country', 'country', 'last_modified'])

        admin_regions = AdminRegion.objects.filter(organisation_country__isnull=False)
        for admin_region in admin_regions:
            admin_region.country = countries[admin_region.organisation_country.country_id]
            admin_region.organisation_country = None
            admin_region.save(update_fields=['organisation_country', 'country', 'last_modified'])
    else:
        organisations = Organisation.objects.filter(organisation_country__isnull=True)
        for organisation in organisations:
            organisation.organisation_country = organisation_countries[organisation.country_id]
            organisation.save(update_fields=['organisation_country', 'last_modified'])

        admin_regions = AdminRegion.objects.filter(organisation_country__isnull=True)
        for admin_region in admin_regions:
            admin_region.organisation_country = organisation_countries[admin_region.country_id]
            admin_region.save(update_fields=['organisation_country', 'last_modified'])


def forward_update_organisation_country(apps, schema_editor):
    update_organisation_country(apps)


def reverse_update_organisation_country(apps, schema_editor):
    update_organisation_country(apps, reverse=True)


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0016_auto_20170224_2308'),
    ]

    operations = [
        migrations.RunPython(forward_update_organisation_country, reverse_code=reverse_update_organisation_country),
    ]
