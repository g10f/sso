# -*- coding: utf-8 -*-
import urllib2
import json
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from sso.accounts.models import Organisation

import logging 
logger = logging.getLogger(__name__)

class Command(NoArgsCommand):
    help = "Load Buddhist Organisations."  # @ReservedAssignment
    url = "https://center.dwbn.org/organisations/buddhistcenter/"
    
    def handle(self, *args, **options):
        if len(args) > 0:
            self.url = args[0]
        try:
            load_organisations(self.url)
        except Exception, e: 
            logger.error(e)

def load_organisations(url):
    conn = urllib2.Request(url)
    f = urllib2.urlopen(conn)
    organisations = json.load(f, encoding="utf-8")

    for organisation in organisations:
        defaults = {'name': organisation['name'],
                    'iso2_code': organisation['country_iso2_code'],
                    'email': organisation['email']}
        try:
            organisation = Organisation.objects.get(uuid=organisation['uuid'])
            for key in defaults:
                setattr(organisation, key, defaults[key])
            organisation.save()
        except ObjectDoesNotExist:
            organisation = Organisation(uuid=organisation['uuid'], **defaults)
            organisation.save()
