import re
from django.core.management.base import NoArgsCommand
from l10n.models import CountryCallingCode
from ...models import OrganisationPhoneNumber

import logging 
logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    help = "Update country calling codes."  # @ReservedAssignment
    
    def handle(self, *args, **options):
        try:
            check_national_phone_numbers()
        except Exception, e:
            logger.error(e)


def check_national_phone_numbers():
    pattern = r"^\s*\(?\+\s*(?P<calling_code>\d+)\)?\s*(?P<phone>.*)"
    prog = re.compile(pattern)

    for organisation_phone_number in OrganisationPhoneNumber.objects.filter(country_calling_code__isnull=True):
        m = prog.match(organisation_phone_number.phone)
        if m:
            m.groupdict()
            calling_code = m.groupdict()['calling_code']
            # phone = m.groupdict()['phone']
            try:
                CountryCallingCode.objects.get(calling_code=calling_code)
            except CountryCallingCode.DoesNotExist:
                print organisation_phone_number.organisation, "'%s'" % organisation_phone_number.phone, "country calling code '%s' does not exist" % calling_code
        else:
            print organisation_phone_number.organisation, "'%s'" % organisation_phone_number.phone, "phone number does not include country calling code"

