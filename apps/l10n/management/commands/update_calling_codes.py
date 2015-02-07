import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from l10n.models import Country, CountryCallingCode

class Command(BaseCommand):
    args = ''
    help = 'update country calling codes.'

    def handle(self, *args, **options):
        file_name = os.path.join(settings.BASE_DIR, '../data/countries.json')
        with open(file_name) as countries_file:
            countries = json.load(countries_file)

            for country in countries:
                try:
                    country_obj = Country.objects.get(iso2_code=country["cca2"])
                    for calling_code in country["callingCode"]:
                        CountryCallingCode.objects.get_or_create(calling_code=calling_code, defaults={'country': country_obj})
                except Country.DoesNotExist:
                    print country["cca2"]
                except Exception, e:
                    print calling_code
                    print e

