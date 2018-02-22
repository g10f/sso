from __future__ import unicode_literals
from django.utils.text import slugify

from django.db import migrations
from sso.organisations.models import default_unique_slug_generator


def update_slug(apps, reverse=False):
    # We can't import the Organisation model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Organisation = apps.get_model("organisations", "Organisation")
    if reverse:
        organisations = Organisation.objects.exclude(slug="")
        for organisation in organisations:
            organisation.slug = ""
            organisation.save(update_fields=['slug', 'last_modified'])
    else:
        organisations = Organisation.objects.filter(slug="")
        for organisation in organisations:
            organisation.slug = default_unique_slug_generator(slugify(organisation.name), Organisation, organisation)
            organisation.save(update_fields=['slug', 'last_modified'])


def forward_update_slug(apps, schema_editor):
    update_slug(apps)


def reverse_update_slug(apps, schema_editor):
    update_slug(apps, reverse=True)


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0002_organisation_slug'),
    ]

    operations = [
        migrations.RunPython(forward_update_slug, reverse_code=reverse_update_slug),
    ]
