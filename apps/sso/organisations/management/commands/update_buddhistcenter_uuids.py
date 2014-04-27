# -*- coding: utf-8 -*-
import urllib2
import json
from django.core.management.base import NoArgsCommand
from ...models import Organisation

import logging 
logger = logging.getLogger(__name__)

class Command(NoArgsCommand):
    help = "Load Buddhist Organisations."  # @ReservedAssignment
    url = "https://centerdb.dwbn.org/association/buddhistorganisation/"
    
    def handle(self, *args, **options):
        if len(args) > 0:
            self.url = args[0]
        try:
            update_buddhistcenter_uuids(self.url)
        except Exception, e: 
            logger.error(e)

def update_buddhistcenter_uuids(url):
    conn = urllib2.Request(url)
    f = urllib2.urlopen(conn)
    centers = json.load(f, encoding="utf-8")

    for center in centers:
        defaults = {'name': center['name'],
                    'email': center['email'],
                    'uuid': center['uuid'],
                    'center_type': '1'}
        centerid = center['centerid']
        if centerid:
            organisation, created = Organisation.objects.get_or_create(centerid=center['centerid'], defaults=defaults)
            if not created:
                organisation.uuid = center['uuid']
                organisation.save()
