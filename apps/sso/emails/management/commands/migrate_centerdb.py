# -*- coding: utf-8 -*-
import os
import re
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.conf import settings
from l10n.models import Country
from sso.utils.ucsv import UnicodeReader, list_from_csv, dic_from_csv
from sso.emails.models import GroupEmail, Email, EmailForward, EmailAlias
from sso.emails.models import GROUP_EMAIL_TYPE, COUNTRY_EMAIL_TYPE, COUNTRY_GROUP_EMAIL_TYPE, REGION_EMAIL_TYPE, CENTER_EMAIL_TYPE, PERM_DWB, PERM_EVERYBODY
from sso.organisations.models import OrganisationCountry, CountryGroup, AdminRegion, Organisation

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update Groups'  # @ReservedAssignment

    """
    _country_groups.txt
    _regions.txt
    centerlist.txt
    emailliste.txt
    mailinglistmembers_gunnar.txt
    centerforwards_gunnar.txt
    guide_email_gunnar.txt
    """
    def handle(self, *args, **options):
        # update_country_groups()
        # update_centers()
        # update_countries()
        update_email_groups()
        # update_center_forwards()
        # update_guide_emails()


def update_guide_emails():
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/guide_email_gunnar.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, delimiter=';')      
        guide_emails = dic_from_csv(reader, key_column=1)

    for (email_value, guide_email) in guide_emails.items():
        name = guide_email['City']
        try:
            email_obj = Email.objects.get(email=email_value.lower())
            try:
                group_email = email_obj.groupemail
                group_email.is_guide_email = True
                group_email.name = name
                group_email.save()
            except ObjectDoesNotExist:
                GroupEmail.objects.create(name=name, email=email_obj, is_guide_email=True)
                
        except ObjectDoesNotExist:
            email_obj = Email.objects.create(email=email_value.lower(), email_type=GROUP_EMAIL_TYPE, permission=PERM_EVERYBODY)
            GroupEmail.objects.get_or_create(name=name, email=email_obj, is_guide_email=True)
            
        forward_value = guide_email['ForwardEmail'].lower()
        if forward_value:
            EmailForward.objects.get_or_create(email=email_obj, forward=forward_value, primary=True)
        
        for name in ['ForwardEmailAlias1', 'ForwardEmailAlias2', 'ForwardEmailAlias3', 'ForwardEmailAlias4']:
            forward_value = guide_email[name].lower()
            if forward_value:
                EmailForward.objects.get_or_create(email=email_obj, forward=forward_value)
        
        for name in ['DWBNEmailALias1', 'DWBNEmailALias2']:
            alias_value = guide_email[name].lower()
            if alias_value:
                EmailAlias.objects.get_or_create(email=email_obj, alias=alias_value)
        

def update_center_forwards():
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/centerforwards_gunnar.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="UTF-8", delimiter=';')      
        centerforwards = dic_from_csv(reader)

    for (center, forward) in centerforwards.items():
              
        email_value = forward['DWBEmail'].lower()
        try:
            email_obj = Email.objects.get(email=email_value, email_type=CENTER_EMAIL_TYPE)
            
            forward_value = forward['ForwardEmail'].lower()
            if forward_value:
                EmailForward.objects.get_or_create(email=email_obj, forward=forward_value, primary=True)
            
            for name in ['ForwardEmailAlias1', 'ForwardEmailAlias2', 'ForwardEmailAlias3', 'ForwardEmailAlias4']:
                forward_value = forward[name].lower()
                if forward_value:
                    EmailForward.objects.get_or_create(email=email_obj, forward=forward_value)
            
            for name in ['DWBNEmailALias1', 'DWBNEmailALias2']:
                alias_value = forward[name].lower()
                if alias_value:
                    EmailAlias.objects.get_or_create(email=email_obj, alias=alias_value)
        except ObjectDoesNotExist:
            logger.warning("%s center email %s not found" % (center, email_value))


def update_country_groups():
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/_country_groups.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, delimiter=';')      
        country_groups_dict = dic_from_csv(reader)

    for (email, country_group) in country_groups_dict.items():
        name = email.split('@')[0].title()
        email_obj = Email.objects.get_or_create(email=email.lower(), email_type=COUNTRY_GROUP_EMAIL_TYPE, defaults={'permission': country_group['permission']})[0]
        CountryGroup.objects.get_or_create(name=name, email=email_obj)


def update_centers():
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/_regions.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="UTF-8", delimiter=';')      
        regions = dic_from_csv(reader)
    
    for _id in regions:
        region = regions[_id]
        country = Country.objects.get(iso2_code=region['Country'])
        email_value = region['Email']
        if email_value:
            email_obj = Email.objects.get_or_create(email=region['Email'].lower(), email_type=REGION_EMAIL_TYPE, defaults={'permission': PERM_DWB})[0]
        else:
            email_obj = None
        region['admin_region'] = AdminRegion.objects.get_or_create(name=region['Name'], email=email_obj, country=country)[0]

    file_name = os.path.join(settings.BASE_DIR, '../data/migration/centerlist.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="UTF-8", delimiter=';')
        centers = dic_from_csv(reader)
    
    for centerid in centers:
        center = centers[centerid]
        try:
            save = False
            organisation = Organisation.objects.get(centerid=centerid)
            if (center['Subregion_ID'] in regions) and (organisation.admin_region != regions[center['Subregion_ID']]['admin_region']):
                organisation.admin_region = regions[center['Subregion_ID']]['admin_region']
                save = True
            if organisation.coordinates_type != center['Coordinates']:
                organisation.coordinates_type = center['Coordinates']
                save = True
            if not organisation.email and center['DWBEmail']:
                defaults = {'email_type': CENTER_EMAIL_TYPE, 'permission': PERM_EVERYBODY}
                organisation.email = Email.objects.get_or_create(email=center['DWBEmail'].lower(), defaults=defaults)[0]
                save = True
            if save:
                organisation.save()
                
        except ObjectDoesNotExist:
            logger.warning("Center %s not found" % center)


def update_email_groups():
    """
    call this last!
    all email objects which are not existing are created as email groups 
    """
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/mailinglistmembers_gunnar.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="ISO-8859-1", delimiter=';')      
        group_list = list_from_csv(reader)
    
    groups = {}
    for row in group_list:
        email = row['email'].lower()
        if email not in groups:
            groups[email] = {'permission': row['permission'], 'forwards': []}        
        if row['forward']:
            groups[email]['forwards'].append(row['forward'])
    
    for (email, group) in groups.items():
        name = email.split('@')[0].title()
        try:
            email_obj = Email.objects.get(email=email)
            # only create a GroupEmail if the Email does not exist
            # GroupEmail.objects.get_or_create(name=name, email=email_obj)
        except ObjectDoesNotExist:
            email_obj = Email.objects.create(email=email.lower(), email_type=GROUP_EMAIL_TYPE, permission=group['permission'])
            GroupEmail.objects.get_or_create(name=name, email=email_obj)
        
        for forward in group['forwards']:
            EmailForward.objects.get_or_create(email=email_obj, forward=forward.lower())


def update_countries():
    country_map = {
        'Russia': 'RU',
        'USA': 'US',
        'UK': 'GB',
        'Yugoslavia': 'MK',
        'SerbiaMontenegro': 'RS'
    }
    
    file_name = os.path.join(settings.BASE_DIR, '../data/migration/emailliste.txt')
    with open(file_name, 'rb') as csvfile:
        reader = UnicodeReader(csvfile, encoding="ISO-8859-1", delimiter=';')      
        countries = dic_from_csv(reader)
    
    for country in countries:
        name = country.split('@')[0]
         
        if name in country_map:
            iso2_code = country_map[name]           
        else:
            name = re.sub("([a-z])([A-Z])", "\g<1> \g<2>", name)  # CamelCase to space separated
            try:            
                iso2_code = Country.objects.get(name__iexact=name).iso2_code
            except ObjectDoesNotExist:
                continue
        
        email = country.lower()
        try:
            email_obj = Email.objects.get(email=email)  # , email_type=COUNTRY_EMAIL_TYPE)
        except ObjectDoesNotExist:
            email_obj = Email.objects.create(email=email.lower(), email_type=COUNTRY_EMAIL_TYPE, permission=PERM_DWB)
        if email_obj.email_type != COUNTRY_EMAIL_TYPE:
            logger.warning("email %s already exists with email_type %s" % (email_obj, email_obj.email_type))
            
        try:
            organisation_country = OrganisationCountry.objects.get(country__iso2_code=iso2_code)
            organisation_country.email = email_obj
            organisation_country.save()
        except ObjectDoesNotExist:
            country = Country.objects.get(iso2_code=iso2_code)
            OrganisationCountry.objects.create(country=country, email=email_obj)
