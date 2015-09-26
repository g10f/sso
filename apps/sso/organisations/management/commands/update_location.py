# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from django.contrib.gis import geos
from django.conf import settings
from geopy.geocoders import GoogleV3
from ...models import Organisation

import logging 
logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    help = "Update locations."  # @ReservedAssignment
    
    def handle(self, *args, **options):
        try:
            update_location()
        except Exception as e:
            logger.error(e)        


def geocode_address(address, components=None):
    address = address.encode('utf-8')
    geocoder = GoogleV3(api_key=settings.SSO_GOOGLE_GEO_API_KEY, scheme='https')
    return geocoder.geocode(address)


def update_location():
    for organisation in Organisation.objects.all().prefetch_related('organisationaddress_set', 'organisationaddress_set__country'):
        if organisation.longitude is None:
            for organisationaddress in organisation.organisationaddress_set.all():
                if organisationaddress.primary:
                    components = {'country': organisationaddress.country.iso2_code}
                    if organisationaddress.postal_code:
                        components['postal_code'] = organisationaddress.postal_code
                    address = "%s, %s" % (organisationaddress.street_address, organisationaddress.city) 
                    location = geocode_address(address, components)
                    if location:
                        point = geos.fromstr("POINT(%s %s)" % (location.longitude, location.latitude))
                        organisation.location = point
                        organisation.coordinates_type = '3'  # Exact
                        organisation.save()
        else:
            point = geos.fromstr("POINT(%s %s)" % (organisation.longitude, organisation.latitude))
            organisation.location = point
            organisation.save()
            # print(location.latitude, location.longitude)
