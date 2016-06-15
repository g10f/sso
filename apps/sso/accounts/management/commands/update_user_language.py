# -*- coding: utf-8 -*-
import logging
from collections import OrderedDict

import sys

from django.core.management.base import BaseCommand
from django.utils.translation import get_language_info
from django.utils.translation.trans_real import get_supported_language_variant
from sso.accounts.models import User
from sso.organisations.models import OrganisationCountry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update user language'  # @ReservedAssignment
    
    def handle(self, *args, **options):
        update_user_language()

iso2_2_language = {
    'am': 'ru',  # Armenia -> Russian
    'ar': 'es',  # Argentina -> Spanish
    'at': 'de',  # Austria -> German
    'au': 'en-au',  # Australia -> Australian English
    'be': 'nl',  # Belgium -> Dutch
    'bg': 'bg',  # Bulgaria -> Bulgarian
    'br': 'pt',  # Brazil -> Portuguese
    'by': 'be',  # Belarus -> Belarusian
    'ca': 'en',  # Canada -> English
    'ch': 'de',  # Switzerland -> German
    'cl': 'es',  # Chile -> Spanish
    'co': 'es-co',  # Colombia -> Colombian Spanish
    'cr': 'es',  # Costa Rica -> Spanish
    'cu': 'es',  # Cuba -> Spanish
    'cz': 'cs',  # Czech Republic -> Czech
    'de': 'de',  # Germany -> German
    'dk': 'da',  # Denmark -> Danish
    'ee': 'et',  # Estonia -> Estonian
    'es': 'es',  # Spain -> Spanish
    'fi': 'fi',  # Finland -> Finnish
    'fr': 'fr',  # France -> French
    'gb': 'en-gb',  # United Kingdom -> British English
    'ge': 'ka',  # Georgia -> Georgian
    'gr': 'el',  # Greece -> Greek
    'gt': 'es',  # Guatemala -> Spanish
    'hk': 'en',  # Hong Kong -> English
    'hr': 'hr',  # Croatia -> Croatian
    'hu': 'hu',  # Hungary -> Hungarian
    'ie': 'ga',  # Ireland -> Irish
    'il': 'he',  # Israel -> Hebrew
    'is': 'is',  # Iceland -> Icelandic
    'it': 'it',  # Italy -> Italian
    'jp': 'ja',  # Japan -> Japanese
    'kg': 'ru',  # Kyrgyzstan -> Russian
    'kr': 'ko',  # South Korea -> Korean
    'kz': 'kk',  # Kazakhstan -> Kazakh
    'lt': 'lt',  # Lithuania -> Lithuanian
    'lv': 'lv',  # Latvia -> Latvian
    'md': 'ro',  # Moldova -> Romanian
    'me': 'sr',  # Montenegro -> Serbian
    'mk': 'mk',  # Macedonia -> Macedonian
    'mt': 'en',  # Malta -> English
    'mx': 'es-mx',  # Mexico -> Mexican Spanish
    'nl': 'nl',  # Netherlands -> Dutch
    'no': 'nb',  # Norway -> Norwegian Bokmal
    'np': 'ne',  # Nepal -> Nepali
    'nz': 'en',  # New Zealand -> English
    'pe': 'es',  # Peru -> Spanish
    'pl': 'pl',  # Poland -> Polish
    'pt': 'pt',  # Portugal -> Portuguese
    'ro': 'ro',  # Romania -> Romanian
    'rs': 'sr',  # Serbia -> Serbian
    'ru': 'ru',  # Russia -> Russian
    'se': 'sv',  # Sweden -> Swedish
    'si': 'sl',  # Slovenia -> Slovenian
    'sk': 'sk',  # Slovakia -> Slovak
    'sv': 'es',  # El Salvador -> Spanish
    'tw': 'zh-hant',  # Taiwan -> Traditional Chinese
    'ua': 'uk',  # Ukraine -> Ukrainian
    'us': 'en',  # United States -> English
    'uy': 'es',  # Uruguay -> Spanish
    've': 'es-ve',  # Venezuela -> Venezuelan Spanish
    'vn': 'vi',  # Viet Nam -> Vietnamese
    'za': 'en',  # South Africa -> English
}


def _iso2_2_language():
    country_languages = {}
    for organisation_country in OrganisationCountry.objects.all():
        country = organisation_country.country
        iso2_code = country.iso2_code.lower()
        language = iso2_2_language.get(iso2_code)

        if language is None:
            print('missing: ', iso2_code)
            continue

        if country_languages.get(iso2_code) is None:
            try:
                language = get_supported_language_variant(language)
                country_languages[iso2_code] = {'country': country, 'language_info': get_language_info(language)}
            except LookupError as e:
                print(e)

    # print country_languages
    cl = OrderedDict(sorted(country_languages.items(), key=lambda t: t[0]))
    for key in cl:
        print("\t'{}': '{}',  # {} -> {}".format(key, cl[key]['language_info']['code'], cl[key]['country'], cl[key]['language_info']['name']))


def update_user_language():
    for user in User.objects.filter(language='').exclude(organisations=None):
        country = user.organisations.first().country
        iso2_code = country.iso2_code.lower()
        user.language = iso2_2_language[iso2_code]
        user.save(update_fields=['language'])
        sys.stdout.write('.')
        sys.stdout.flush()
