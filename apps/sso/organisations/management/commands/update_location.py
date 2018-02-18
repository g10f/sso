# -*- coding: utf-8 -*-
from time import sleep
from django.core.management.base import BaseCommand
from django.contrib.gis import geos
from django.conf import settings
from geopy.geocoders import GoogleV3
from ...models import Organisation

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update locations."  # @ReservedAssignment

    def handle(self, *args, **options):
        try:
            update_location()
        except Exception as e:
            logger.error(e)


def geocode_address(address, components=None):
    sleep(0.1)  # google allows max. 10 request per second
    address = address.encode('utf-8')
    geocoder = GoogleV3(api_key=settings.SSO_GOOGLE_GEO_API_KEY, scheme='https')
    return geocoder.geocode(address)


def update_location():
    for organisation in Organisation.objects.filter(location__isnull=True).prefetch_related('organisationaddress_set',
                                                                    'organisationaddress_set__country'):
        organisationaddress = organisation.organisationaddress_set.filter(address_type='physical').first()
        location = None
        coordinates_type = ''
        if organisationaddress:
            components = {'country': organisationaddress.country.iso2_code}
            if organisationaddress.postal_code:
                components['postal_code'] = organisationaddress.postal_code
            address = "%s, %s" % (organisationaddress.street_address, organisationaddress.city)
            location = geocode_address(address, components)
            if location:
                coordinates_type = '3'
            else:
                components = {'country': organisationaddress.country.iso2_code}
                if organisationaddress.postal_code:
                    components['postal_code'] = organisationaddress.postal_code
                address = "%s" % organisationaddress.city
                location = geocode_address(address, components)
                if location:
                    coordinates_type = '2'

        if not location:
            components = {'country': organisation.organisation_country.country.iso2_code}
            address = "%s" % organisation.name
            location = geocode_address(address, components)
            if location:
                coordinates_type = '2'

        if location:
            print("{}, {}, {}, {}".format(coordinates_type, location.longitude, location.latitude, organisation))
            point = geos.fromstr("POINT(%s %s)" % (location.longitude, location.latitude))
            organisation.location = point
            organisation.coordinates_type = coordinates_type
            organisation.save()
