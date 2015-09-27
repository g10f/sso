# -*- coding: utf-8 -*-
import os
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.conf import settings
from sso.utils.ucsv import UnicodeReader, dic_from_csv
from sso.organisations.models import OrganisationCountry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import Country URLs'  # @ReservedAssignment

    """
    country_urls.txt
    """
    def handle(self, *args, **options):
        import_country_urls()


def import_country_urls():
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/country_urls.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, delimiter=';')      
        country_urls = dic_from_csv(reader)

    for (country, value) in country_urls.items():
        url = value['URL']
        try:
            org_country = OrganisationCountry.objects.get(country__printable_name__icontains=country)
            if not org_country.homepage:
                org_country.homepage = url
                org_country.save()
        except ObjectDoesNotExist:
            print("country %s not found" % country)
