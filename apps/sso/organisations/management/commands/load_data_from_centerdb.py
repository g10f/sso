# -*- coding: utf-8 -*-
import json
import decimal 
from django.utils.dateparse import parse_date
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from django.utils.six.moves.urllib.request import Request, urlopen
from ...models import Organisation, OrganisationAddress, OrganisationPhoneNumber, OrganisationCountry
from sso.emails.models import Email, CENTER_EMAIL_TYPE

from l10n.models import Country  # , AdminArea
from sso.models import update_object_from_dict

import logging 
logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    help = "Load Buddhist Organisations."  # @ReservedAssignment
    url = "https://center.dwbn.org/organisations/buddhistcenter/"
    # url = "http://localhost:8002/organisations/buddhistcenter/"
    
    def handle(self, *args, **options):
        if len(args) > 0:
            self.url = args[0]
        try:
            load_buddhistcenters(self.url)
        except Exception as e:
            logger.error(e)        
        

def get_json(url):
    conn = Request(url)
    f = urlopen(conn)
    return json.load(f, encoding="utf-8")


def get_self_url(links):
    for link in links:
        if link['rel'] == 'self':
            return link['href']


def update_adresses(addresses, organisation):
    address_type_map = {
        'post': 'post',
        'physical': 'meditation',
    }
    for address_item in addresses:
        new_address_type = address_item['address_type']
        if new_address_type in address_type_map:
            address_item['address_type'] = address_type_map[new_address_type]
        else:
            logger.error("Loading Data from centerdb: address type %s not supported." % new_address_type)

    def get_address_by_type(address_type):
        for item in addresses:
            if item['address_type'] == address_type:
                return item

    for address_type in OrganisationAddress.ADDRESSTYPE_CHOICES:
        address_item = get_address_by_type(address_type[0])
        if address_item:
            country = Country.objects.get(iso2_code=address_item['country_iso2_code'])
            address, created = OrganisationAddress.objects.get_or_create(address_type=address_type[0], organisation=organisation, defaults={'country': country})
            address_item['country'] = country
            update_object_from_dict(address, address_item, key_mapping={'is_default_postal': 'primary', 'state': 'region' })
        else:
            try:
                address = OrganisationAddress.objects.get(address_type=address_type[0], organisation=organisation)
                address.delete()
            except ObjectDoesNotExist:
                pass


def update_phonenumbers(phonenumbers, organisation):
    phone_type_map = {
        'private': 'home',
        'other2': 'other',
        'other3': 'other2',
        'faxprivate': 'fax',
        'mobile': 'mobile',
        'mobile2': 'mobile2'
    }
    for phonenumber_item in phonenumbers:
        new_phone_type = phonenumber_item['phone_type']
        if new_phone_type in phone_type_map:
            phonenumber_item['phone_type'] = phone_type_map[new_phone_type]
        else:
            logger.error("Loading Data from centerdb: phone type %s not supported." % new_phone_type)

    def has_phone_type(type):
        for item in phonenumbers:
            if item['phone_type'] == type:
                return True

    # Delete types we don't get anymore
    for phonenumber in OrganisationPhoneNumber.objects.filter(organisation=organisation):
        if not has_phone_type(phonenumber.phone_type):
            phonenumber.delete()

    for phonenumber_item in phonenumbers:
        phonenumber = OrganisationPhoneNumber.objects.filter(organisation=organisation, phone_type=phonenumber_item['phone_type']).first()
        if phonenumber is None:
            phonenumber = OrganisationPhoneNumber.objects.create(organisation=organisation, phone_type=phonenumber_item['phone_type'], phone=phonenumber_item['phone'])

        update_object_from_dict(phonenumber, phonenumber_item)


def mark_active_centers(active_center_uuids):
    for center in Organisation.objects.all():
        
        is_active = True if center.uuid.hex in active_center_uuids else False
        
        if center.is_active != is_active:
            center.is_active = is_active
            center.save()


def load_buddhistcenters(url):    
    def get_country(value):
        try:
            country = Country.objects.get(iso2_code=value)
            OrganisationCountry.objects.get_or_create(country=country)
            return country
        except ObjectDoesNotExist as e:
            logger.warning("exception %s, country_id: %s", str(e), value)            
        return None
    
    def get_email(value):
        email = Email.objects.filter(email=value).first()
        if not email:
            email = Email(email=value.lower(), email_type=CENTER_EMAIL_TYPE)
            email.save()
        return email
        
    def float_to_decimal(value):
        # manual conversion, to avoid having changed values caused by conversion from float 
        # to decimal
        if value is None:
            return value        
        return decimal.Decimal(str(value))
    
    key_mapping = {
        'centertype': 'center_type',
        'last_modified': '',  # ignore 
        'latitude': ('latitude', float_to_decimal),
        'longitude': ('longitude', float_to_decimal),
        'founded': ('founded', parse_date),
        'country_iso2_code': ('country', get_country),
        'email': ('email', get_email),
        'alias': 'name_native'
    }
    
    buddhistcenters = get_json(url)
    active_center_uuids = []
    
    for item in buddhistcenters:
        active_center_uuids.append(item['uuid']) 
        try:
            organisation = Organisation.objects.get(uuid=item['uuid'])
        except ObjectDoesNotExist:
            organisation = Organisation(uuid=item['uuid'])
        
        if item['founded'] == '':
            del item['founded']
            
        update_object_from_dict(organisation, item, key_mapping)
        
        self_url = get_self_url(item['links'])
        if self_url:
            details = get_json(self_url)
            update_adresses(details['addresses'], organisation)
            update_phonenumbers(details['phonenumbers'], organisation)
    
    mark_active_centers(active_center_uuids)
