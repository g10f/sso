# -*- coding: utf-8 -*-
import datetime
import logging

import pytz

from django.core.management.base import NoArgsCommand
from sso.organisations.models import Organisation

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    help = "Update locations."  # @ReservedAssignment
    
    def handle(self, *args, **options):
        try:
            update_timezone()
        except Exception as e:
            logger.error(e)        


def update_timezone():
    organisations = Organisation.objects.raw(
            'SELECT id, name, location, tzid \
             FROM tz_world, organisations_organisation \
             WHERE ST_Contains(tz_world.geom, ST_GeomFromEWKB(organisations_organisation.location))')

    for organisation in organisations:
        organisation.timezone = organisation.tzid
        organisation.save(update_fields=['timezone'])
