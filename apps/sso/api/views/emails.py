# -*- coding: utf-8 -*-
import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required, login_required
from sso.emails.models import Email
from sso.emails.models import REGION_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, COUNTRY_GROUP_EMAIL_TYPE

import logging

logger = logging.getLogger(__name__)

@login_required
@permission_required('emails.read_email', raise_exception=True)
def emails(request):
    # Create the HttpResponse object with the appropriate CSV header.
    # response = HttpResponse(content_type='text/csv')
    response = HttpResponse(content_type='text')
    # response['Content-Disposition'] = 'attachment; filename="emails.csv"'
    response.write('approved: karmapa\r\n')
    writer = csv.writer(response, delimiter=';')
    
    for email in Email.objects.filter(is_active=True, email_type=COUNTRY_GROUP_EMAIL_TYPE).prefetch_related('countrygroup_set__organisationcountry_set__email'):
        for countrygroup in email.countrygroup_set.all():
            for country in countrygroup.organisationcountry_set.all().select_related('email'):
                if country.email:
                    writer.writerow([email, country.email, '', email.permission])
          
    for email in Email.objects.filter(is_active=True, email_type=COUNTRY_EMAIL_TYPE).prefetch_related('organisationcountry_set__country__organisation_set__email',
                                                                                                      'organisationcountry_set__country__adminregion_set__email'):
        for country in email.organisationcountry_set.all():
            for organisation in country.country.organisation_set.all():
                if organisation.email:
                    writer.writerow([email, organisation.email, '', email.permission])
            for adminregion in country.country.adminregion_set.all():
                if adminregion.email:
                    writer.writerow([email, adminregion.email, '', email.permission])

    for email in Email.objects.filter(is_active=True, email_type=REGION_EMAIL_TYPE).prefetch_related('adminregion_set__organisation_set__email'):
        for adminregion in email.adminregion_set.all():
            for organisation in adminregion.organisation_set.all():
                if organisation.email:
                    writer.writerow([email, organisation.email, '', email.permission])
                   
    for email in Email.objects.filter(is_active=True).prefetch_related('emailalias_set'):
        for alias in email.emailalias_set.all():
            writer.writerow([alias, email, '', email.permission])
    
    for email in Email.objects.filter(is_active=True).prefetch_related('emailalias_set', 'emailforward_set'):
        for alias in email.emailalias_set.all():
            writer.writerow([alias, email, '', email.permission])
        for forward in email.emailforward_set.all():
            writer.writerow([email, forward, '', email.permission])
    
    return response
