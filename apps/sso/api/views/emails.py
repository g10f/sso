# -*- coding: utf-8 -*-
import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required, login_required
from sso.emails.models import EmailForward, EmailAlias, PERM_VIP_DWB
from sso.organisations.models import CountryGroup, OrganisationCountry, AdminRegion, Organisation

import logging

logger = logging.getLogger(__name__)


@login_required
@permission_required('emails.read_email', raise_exception=True)
def emails(request, type):  # @ReservedAssignment
    """
    We have 2 special cases:
    1. world@diamondway-center.org is forwarded to every valid country email
    2. <centername>@diamantweg.de is an alias for <centername>@diamondway-center.org for German centers
    """
    rows = []
    # World 
    for country in OrganisationCountry.objects.filter(email__isnull=False, is_active=True):
        rows.append(['world@diamondway-center.org', str(country.email), '', PERM_VIP_DWB])
    
    # Country Groups
    for countrygroup in CountryGroup.objects.filter(email__isnull=False).prefetch_related('email', 'organisationcountry_set__email'):
        for country in countrygroup.organisationcountry_set.all():
            if country.email and country.is_active:
                rows.append([str(countrygroup.email), str(country.email), '', countrygroup.email.permission])
    
    # Countries
    for country in OrganisationCountry.objects.filter(email__isnull=False, is_active=True).prefetch_related('email', 'country__organisation_set__email', 'country__adminregion_set__email'):
        for organisation in country.country.organisation_set.all():
            if organisation.email and organisation.is_active:
                rows.append([str(country.email), str(organisation.email), '', country.email.permission])
        for adminregion in country.country.adminregion_set.all():
            if adminregion.email and adminregion.is_active:
                rows.append([str(country.email), str(adminregion.email), '', country.email.permission])

    # Admin Regions
    for adminregion in AdminRegion.objects.filter(email__isnull=False, is_active=True).prefetch_related('email', 'organisation_set__email'):
        for organisation in adminregion.organisation_set.all():
            if organisation.email and organisation.is_active:
                rows.append([str(adminregion.email), str(organisation.email), '', adminregion.email.permission])

    # diamantweg.de for German Centers
    for organisation in Organisation.objects.filter(email__isnull=False, is_active=True, country__iso2_code='DE').prefetch_related('email'):
        if organisation.email.email:
            email_value = organisation.email.email.split('@')[0] + '@diamantweg.de'
            rows.append([email_value, str(organisation.email), '', organisation.email.permission])
    
    # Forwards
    for forward in EmailForward.objects.filter(email__is_active=True).prefetch_related('email'):
        rows.append([str(forward.email), forward.forward, '', forward.email.permission])
    
    # Alias
    for alias in EmailAlias.objects.filter(email__is_active=True).prefetch_related('email'):
        rows.append([alias.alias, str(alias.email), '', alias.email.permission])
        
    # Create the HttpResponse object with the appropriate CSV header.
    if type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="emails.csv"'
    else:
        response = HttpResponse(content_type='text')
    
    response.write('approved: karmapa\r\n')
    writer = csv.writer(response, delimiter=';')
    writer.writerows(rows)

    return response
