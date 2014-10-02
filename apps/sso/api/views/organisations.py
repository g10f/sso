# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.db.models import Q
from utils.url import base_url
from utils.parse import parse_datetime_with_timezone_support
from sso.organisations.models import Organisation, get_near_organisations
from sso.api.views.generic import JsonListView, JsonDetailView

import logging

logger = logging.getLogger(__name__)


class OrganisationMixin(object):
    model = Organisation

    def get_object_data(self, request, obj, details=False):
        base = base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_organisation', kwargs={'uuid': obj.uuid})),
            'id': u'%s' % obj.uuid,
            'name': u'%s' % obj.name,
            'email': u'%s' % obj.email,
            'founded': obj.founded,
            'center_type': obj.center_type,
            'homepage': obj.homepage,
            'country': obj.country.iso2_code,
            'last_modified': obj.last_modified,
        }
        try:
            # if we have a gis query
            data['distance'] = "%.1f km" % obj.distance.km
        except AttributeError:
            pass
        if not obj.is_private:
            if obj.location:
                data['location'] = {'geo': {'latitude': obj.location.y, 'longitude': obj.location.x}}
            
        if details:
            if not obj.is_private:
                data['addresses'] = {
                    address.uuid: {
                        'address_type': address.address_type,
                        'name': address.addressee,
                        'street_address': address.street_address,
                        'city': address.city,
                        'postal_code': address.postal_code,
                        'country': address.country.iso2_code,
                        'region': address.region,
                        'primary': address.primary
                    } for address in obj.organisationaddress_set.all()
                }
            data['phone_numbers'] = {
                phone_number.uuid: {
                    'phone_type': phone_number.phone_type,
                    'phone': phone_number.phone,
                    'primary': phone_number.primary
                } for phone_number in obj.organisationphonenumber_set.all()
            }
        return data
    

class OrganisationDetailView(OrganisationMixin, JsonDetailView):
    http_method_names = ['get', 'options']
    permissions_tests = {
        'get': lambda u, obj: u.is_authenticated(),
    }
    operation = {}
    
    def get_queryset(self):
        return super(OrganisationDetailView, self).get_queryset().prefetch_related('country', 'email', 'organisationaddress_set', 'organisationphonenumber_set')

    def get_object_data(self, request, obj):
        return super(OrganisationDetailView, self).get_object_data(request, obj, details=True)

    def delete_object(self, request, obj):
        obj.is_active = False
        obj.save()


class OrganisationList(OrganisationMixin, JsonListView):
    permissions_tests = {
        'get': lambda u, x: u.is_authenticated()
    }

    def get_queryset(self):
        qs = super(OrganisationList, self).get_queryset().filter(is_active=True).prefetch_related('country', 'email')
        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(name__icontains=name)
        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(country__iso2_code__iexact=country)
            
        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed) | Q(organisationaddress__last_modified__gte=parsed) | Q(organisationphonenumber__last_modified__gte=parsed))
         
        latlng = self.request.GET.get('latlng', None) 
        
        if latlng:
            (lat, lng) = tuple(latlng.split(','))
            from django.contrib.gis import geos
            dlt = self.request.GET.get('dlt', None)
            if dlt:
                dlt = dlt.split()
                if len(dlt) < 2:
                    dlt.append('km')
                distance = {dlt[1]: dlt[0]}
            else:
                distance = None
            
            point = geos.fromstr("POINT(%s %s)" % (lng, lat))
            qs = get_near_organisations(point, distance, qs)

        return qs
