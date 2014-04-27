# -*- coding: utf-8 -*-
import urllib2
from datetime import datetime
import re
import HTMLParser
from decimal import Decimal
from xml.etree import ElementTree

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import translation

from l10n.models import AdminArea, Country
from sso.models import update_object_from_dict
from ...models import OrganisationAddress, OrganisationPhoneNumber, Organisation  # Address, BuddhistCenter, PhoneNumber

import logging 

logger = logging.getLogger(__name__)

_baseurl = "http://kagyu.net/XML2.asp"


def translate_text(text, language):
    cur_language = translation.get_language()
    if language == cur_language:
        return translation.ugettext(text)
        
    try:
        translation.activate(language)
        text = translation.ugettext(text)
    finally:
        translation.activate(cur_language)
    return text


def _get_city_postal_and_state(value, country):
    _canadian_postcode = "[ABCEGHJKLMNPRSTVXY]\d[A-Z] \d[A-Z]\d" 
    _uk_postcode = "([A-PR-UWYZ0-9][A-HK-Y0-9][AEHMNPRTVXY0-9]?[ABEHMNPRVWXY0-9]? {1,2}[0-9][ABD-HJLN-UW-Z]{2}|GIR 0AA)"
    _rg_stadt = {
                 'default': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d\-\s]+) (?P<city>[\D\s]+)$",
                 'AR': r"(?P<postal_code>\w+) (?P<city>[\D\s]+)$",
                 'CA': r"(?P<city>[a-zA-Z]{3,99}( [a-zA-Z]{4,99})?),? ?(?P<state>(([A-Z]{2}\.?)|([a-zA-Z]{3,99}( [a-zA-Z]{4,99})?))) ?(?P<postal_code>(%s))$" % _canadian_postcode,
                 'AU': r"(?P<city>\w+)[\s,]{1,3}(?P<state>[A-Z]{2,3}) (?P<postal_code>\d+)$",
                 'NL': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d]{4}) ?(?P<city>[\D\s]+)$",
                 'GB': r"(?P<city>[a-zA-Z]{2,99}( [a-zA-Z]{3,99})?(,? [a-zA-Z]{3,99})?),? (?P<postal_code>(%s))$" % _uk_postcode,
                 'US': r"(?P<city>[a-zA-Z]{2,99}( [a-zA-Z]{3,99})?),? ?(?P<state>[a-zA-Z]{2,5})? ?(?P<postal_code>(\d{5}))$",
                 'VE': r"(?P<city>\w+) (?P<postal_code>\d+)$",
                 }
    rg = _rg_stadt.get(country.iso2_code)
    if (not rg): 
        rg = _rg_stadt.get('default')
    
    m = re.match(rg, value)
    if m:
        result = m.groupdict()
        for key in result:
            if result[key] is None:
                result[key] = ''                
        return result
    else:
        return []

    
def _split_city(city, country):    
    _canadian_postcode = "[ABCEGHJKLMNPRSTVXY]\d[A-Z] \d[A-Z]\d" 
    _uk_postcode = "([A-PR-UWYZ0-9][A-HK-Y0-9][AEHMNPRTVXY0-9]?[ABEHMNPRVWXY0-9]? {1,2}[0-9][ABD-HJLN-UW-Z]{2}|GIR 0AA)"
    _rg_stadt = {
                 'default': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d\-\s]+) (?P<city>[\D\s]+)",
                 'AR': r"(?P<postal_code>\w+) (?P<city>[\D\s]+)",
                 'CA': r"(?P<city>[a-zA-Z]{3,99}( [a-zA-Z]{4,99})?),? ?(?P<state>(([A-Z]{2}\.?)|([a-zA-Z]{3,99}( [a-zA-Z]{4,99})?))) ?(?P<postal_code>(%s)?)" % _canadian_postcode,
                 'AU': r"(?P<city>\w+)[\s,]{1,3}(?P<state>[A-Z]{2,3}) (?P<postal_code>\d+)",
                 'NL': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d]{4}) ?(?P<city>[\D\s]+)",
                 'GB': r"(?P<city>[a-zA-Z]{2,99}( [a-zA-Z]{3,99})?(,? [a-zA-Z]{3,99})?),? (?P<postal_code>(%s)?)" % _uk_postcode,
                 'US': r"(?P<city>[a-zA-Z]{2,99}( [a-zA-Z]{3,99})?),? ?(?P<state>[a-zA-Z]{2,5})? ?(?P<postal_code>(\d{5}))?",
                 'VE': r"(?P<city>\w+) (?P<postal_code>\d+)",
                 }
    rg = _rg_stadt.get(country.iso2_code)
    if (not rg): 
        rg = _rg_stadt.get('default')
    
    m = re.match(rg, city)
    if m:
        result = m.groupdict()
        for key in result:
            if result[key] is None:
                result[key] = ''                
        return result
    else:
        return {'city': city}

def _get_text(text):
    if text is None:
        return ''
    else:
        return text
    
def _get_postal_code(country, postal_code):
    _canadian_postcode = "[ABCEGHJKLMNPRSTVXY]\d[A-Z] \d[A-Z]\d" 
    _uk_postcode = "([A-PR-UWYZ0-9][A-HK-Y0-9][AEHMNPRTVXY0-9]?[ABEHMNPRVWXY0-9]? {1,2}[0-9][ABD-HJLN-UW-Z]{2}|GIR 0AA)"
    _rg_postal_code = {
                 'default': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d\-\s]+)",
                 'AR': r"(?P<postal_code>\w+)",
                 'CA': r"(?P<postal_code>(%s)?)" % _canadian_postcode,
                 'AU': r"(?P<state>[A-Z]{2,3}) (?P<postal_code>\d+)",
                 'NL': r"([A-Z]{1,3}\-?)?(?P<postal_code>[\d]{4})",
                 'GB': r"(?P<postal_code>(%s)?)" % _uk_postcode,
                 'US': r"(?P<state>[a-zA-Z]{2,5})? ?(?P<postal_code>(\d{5}))?",
                 'VE': r"(?P<postal_code>\d+)",
                 }
    rg = _rg_postal_code.get(country.iso2_code)
    if (not rg): 
        rg = _rg_postal_code.get('default')
    
    m = re.match(rg, postal_code)
    if m:
        result = m.groupdict()
        for key in result:
            if result[key] is None:
                result[key] = ''                
        return result
    else:
        return {'postal_code': postal_code}
    

def _has_field(model, fieldname):
    if fieldname in [f.name for f in model._meta.fields]:
        return True
    else:
        return False

def _defaults(cls, dictionary):
    defaults = {
        'street_address': '',
        'city': '',
        'postal_code': '',
        'careof': ''
    }
    for key, value in dictionary.iteritems():
        if _has_field(cls, key):
            defaults[key] = value     
    return defaults 

def _get_addressee(country, buddhistcenter):
    lang = "en"
    try:
        if country.iso2_code in ["DE", "AT", "CH"]: 
            lang = "de"
    except:
        pass
        
    center_type_desc = translate_text(buddhistcenter.center_type_desc(), lang)
    
    return u'%s %s' % (center_type_desc, buddhistcenter.name)
    
def _add_address(address, address_type, country, buddhistcenter):      
    defaults = _defaults(OrganisationAddress, address)
    defaults['state'] = address.get('state')
    defaults['country'] = country
    defaults['addressee'] = _get_addressee(country, buddhistcenter)
    if address_type == 'post': 
        defaults['primary'] = True

    obj, created = OrganisationAddress.objects.get_or_create(address_type=address_type, organisation=buddhistcenter,
                                                 defaults=defaults)
    if not created:
        update_object_from_dict(obj, defaults)
          
def _get_date(value):
    if not value:
        return None
    value = value.replace(' ', '')
    value = value.rstrip('.')
    value = value.lstrip('.')
    try:
        return datetime.strptime(value, '%d.%m.%Y').date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(value, '%Y').date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(value, '%B%Y').date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(value, '%m/%Y').date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(value, '%m.%Y').date()
    except ValueError:
        pass
    
    try:
        return datetime.strptime(value, '%d.%b.%Y').date()
    except ValueError:
        pass
    
    raise ValueError('date format does not match')
                

def _html_unescape(text):
    if text:
        pars = HTMLParser.HTMLParser()
        return pars.unescape(text)
    else:
        return ''
    
def _find_country(name_land):
    _laender_map = {
        'EUROPE CENTER': 'DE',  # 'GERMANY',
        'MACEDONIA': 'MK',  # 'MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF',
        'MOLDAVIA (MOLDOVA)': 'MD',  # 'MOLDOVA, REPUBLIC OF',
        'RUSSIA': 'RU',  # 'RUSSIAN FEDERATION',
        'SLOVAK REPUBLIC': 'SK',  # 'SLOVAKIA',
        'UNITED STATES OF AMERICA': 'US',  # 'UNITED STATES',
        'VIETNAM': 'VN',  # VIET NAM
        'KYRGYZ REPUBLIC (KYRGYZSTAN)': 'KG',
        'SOUTH KOREA': 'KR',
        }
    
    name_land = name_land.upper().rstrip().lstrip()
    iso2_code = _laender_map.get(name_land)
    country = None
    try:
        if iso2_code:
            country = Country.objects.get(iso2_code=iso2_code)
        else:
            country = Country.objects.get(name=name_land)
    except ObjectDoesNotExist, e:
        logger.error(u"%s Country Does Not Exist: %s." % (e, name_land))
    
    return country

def _get_state(country, name):
    state = None
    if name:
        try:
            if len(name) > 3:
                state = AdminArea.objects.get(country=country, name=name)
            else:
                state = AdminArea.objects.get(country=country, abbrev=name)
        except ObjectDoesNotExist:
            pass     
    return state

    
def _analyse_street(country, state, city, postal_code, street):
    _special_tags = {
        'Only Postal address:': 'post',
        'Postal address:': 'post', 
        'Postal:': 'post', 
        'Post:': 'post',
        'Mail:': 'post', 
        'GPO Box': 'post', 
        'PO Box': 'post', 
        'P.O. Box': 'post', 
        'Place of meditations:': 'meditation', 
        'Meditation:': 'meditation',
        'Meditation': 'meditation', 
        'Location:': 'meditation', 
        'Center:': 'meditation', 
    }    
    rg_street = street.split("\n")    
    
    addresses = {'default': []}    
    current = addresses['default']
    for item in rg_street:
        for key, value in _special_tags.iteritems():
            if item.startswith(key):
                assert(addresses.get(value) == None)
                addresses[value] = []
                current = addresses[value]
                if key in ['Only Postal address:', 'Postal address:', 'Postal:', 'Post:', 'Mail:', 'Place of meditations:', 'Meditation:', 'Meditation', 'Location:', 'Center:']:
                    item = item[len(key) + 1:]
                break
        if item:
            current.append(item)
    
    if len(addresses) > 1:  # delete empty default address if we have a post or meditation address
        if len(addresses['default']) == 0:
            del addresses['default']
            
    new_addresses = {}
    for key, value in addresses.iteritems():
        address = {'city': city, 'postal_code': postal_code}
        if not state is None:
            address['state'] = state.abbrev
        if len(value) <= 1:
            address['street_address'] = u'\n'.join(value)
            new_addresses[key] = address
        elif len(value) > 1:
            # we have 2 or more fields, check if the last is a city
            city_postal_and_state = _get_city_postal_and_state(value[-1], country)
            if city_postal_and_state:
                value.pop(-1)  # remove city
                address.update(city_postal_and_state)
                
            address['street_address'] = u'\n'.join(value)
            new_addresses[key] = address 

    return new_addresses
     
def _update_adress(buddhistcenter, rec):
    country = _find_country(rec.find('fldCountry').text)
    city = _html_unescape(rec.find('fldCityLocation').text)
    if not city:
        city = _html_unescape(rec.find('fldCity').text)
    postal_code = _html_unescape(rec.find('fldcode').text)
    street = _html_unescape(rec.find('fldStreet').text)
    careof = _html_unescape(rec.find('fldHost').text)
    
    if not city and not street:
        city = _html_unescape(rec.find('fldCity').text)
        
    # update postcode and city
    state = None
    if not postal_code:
        rg_city = _split_city(city, country)
        postal_code = rg_city.get('postal_code', '')
        state_bez = rg_city.get('state', '')
        city = rg_city['city']
        
        if state_bez: 
            state = _get_state(country, state_bez)
            if not state:
                # probably belongs to the name of the city
                city = u'%s %s' % (city, state_bez)
    else:
        postal_code = _get_postal_code(country, postal_code)['postal_code']

    addresses = _analyse_street(country, state, city, postal_code, street)
    
    # update state and careof
    for value in addresses.itervalues():
        _state = value.get('state') 
        if _state:
            value['state'] = _get_state(country, _state)
        else:
            value['state'] = state

        _careof = value.get('careof')
        if not _careof:
            value['careof'] = careof
        
    if len(addresses) > 2:
        print  addresses 
    if addresses.get('default'):
        if addresses.get('meditation'):
            assert(not addresses.get('post'))
            addresses['post'] = addresses['default']
        else:
            addresses['meditation'] = addresses['default']
            
        del addresses['default']

    if addresses.get('meditation'):        
        _careof = addresses['meditation'].get('careof') 
        if not _careof:
            addresses['meditation']['careof'] = careof
    
    for address_type in OrganisationAddress.ADDRESSTYPE_CHOICES:
        address = addresses.get(address_type[0])
        if address:
            _add_address(address, address_type[0], country, buddhistcenter)
        else:
            try:
                address = OrganisationAddress.objects.get(address_type=address_type[0], organisation=buddhistcenter)
                address.delete()
            except ObjectDoesNotExist:
                pass
        

def _update_phone_numbers(buddhistcenter, rec):
    phone_type_map = {
        'home': 'fldTelefon',
        'other': 'fldTelefon2',
        'other2': 'fldTelefon3',
        'fax': 'fldFax',
        'mobile': 'fldHandy',
        'mobile2': 'fldHandy2'
    }
    for phone_type in phone_type_map:
        phone = rec.find(phone_type_map[phone_type]).text
        if phone:
            #assert(phone_type not in ['other2', 'mobile2'])
            defaults = {'phone': phone}
            phone_number, created = OrganisationPhoneNumber.objects.get_or_create(organisation=buddhistcenter, 
                                                                      phone_type=phone_type, defaults=defaults)
            if not created:
                update_object_from_dict(phone_number, defaults)
        else:
            try:
                phone_number = OrganisationPhoneNumber.objects.get(organisation=buddhistcenter, phone_type=phone_type)
                phone_number.delete()
            except ObjectDoesNotExist:
                pass
    
def _get_coordinate(text):
    text = text.replace(' ', '').replace(',', '.')
    parts = text.split('.')
    if len(parts) > 1:
        parts[1] = parts[1][:6]  # 6 digits
        text = '.'.join(parts)
        
    return Decimal(text)
    
def _update_buddhistcenter(rec): 
    centerid = int(rec.find('fldID').text)
    defaults = {'is_active': True}
    defaults['name'] = _html_unescape(rec.find('fldCity').text)
    defaults['email'] = rec.find('fldDWBEmail').text
    defaults['founded'] = _get_date(rec.find('fldFounded').text)
    defaults['center_type'] = rec.find('fldTyp').text
    defaults['homepage'] = _get_text(rec.find('fldURL').text)
    
    longitude = rec.find('fldLongitude').text
    if longitude:
        defaults['longitude'] = _get_coordinate(longitude)  
    
    latitude = rec.find('fldLatitude').text
    if latitude:
        defaults['latitude'] = _get_coordinate(latitude)  
    
    name = _html_unescape(rec.find('fldCityAlias').text)
    if name:
        defaults['name'] = name
        
    #rg_street = _html_unescape(rec.find('fldStreet').text)
    #rg_street = rg_street.split("\n")
    
    buddhistcenter, created = Organisation.objects.get_or_create(centerid=centerid, defaults=defaults)
    if not created:
        update_object_from_dict(buddhistcenter, defaults)
        
    _update_adress(buddhistcenter, rec)
    _update_phone_numbers(buddhistcenter, rec)        

    return buddhistcenter
        
def load_data_from_diamondway_buddhism_org(filter_func=None):   
    conn = urllib2.Request(_baseurl)
    f = urllib2.urlopen(conn)
    response = f.read()
    elem = ElementTree.XML(response) 
    
    rec_list = elem.findall('rec')
    for rec in rec_list:
        try:
            if filter_func and not filter_func(rec):
                continue
            
            center = _update_buddhistcenter(rec)
            yield center
        except:
            logger.error('Failed to update center. Rec %s', ElementTree.tostring(rec), exc_info=1)

def filter_func(rec):
    return True
    #centerid = int(rec.find('fldID').text)
    #if centerid not in [1121, 1495]:
    #    continue
    
class Command(BaseCommand):
    help = "Import diamondway.org center data"  # @ReservedAssignment
    
    def handle(self, *args, **options):
        
        center_ids = []
        try:
            for center in load_data_from_diamondway_buddhism_org(filter_func):
                logger.info(u"Loaded %d" % (center.centerid))
                center_ids += [center.centerid]
                
            q = Q(centerid__isnull=False) & ~Q(centerid__in=center_ids) 
            Organisation.objects.filter(q).update(is_active=False)
        except Exception, e: 
            logger.exception(e.message)
