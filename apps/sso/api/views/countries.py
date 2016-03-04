# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.db.models import Q
from sso.utils.url import base_url
from sso.utils.parse import parse_datetime_with_timezone_support
from sso.organisations.models import OrganisationCountry
from sso.api.views.generic import JsonListView, JsonDetailView

import logging

logger = logging.getLogger(__name__)


class CountryMixin(object):
    model = OrganisationCountry

    def get_object_data(self, request, obj, details=False):
        base = base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_country', kwargs={'iso2_code': obj.country.iso2_code})),
            'id': u'%s' % obj.uuid.hex,
            'code': obj.country.iso2_code,
            'name': u'%s' % str(obj),
            'email': u'%s' % obj.email,
            'homepage': obj.homepage,
            'last_modified': obj.get_last_modified_deep(),
            'continent': {
                'code': obj.country.continent,
                'name': obj.country.get_continent_display(),
            }
        }
        if details:
            if ('users' in request.scopes) and (obj.country in request.user.get_administrable_user_countries()):
                data['users'] = "%s%s?country=%s" % (base, reverse('api:v2_users'), obj.country.iso2_code)
            if obj.country.organisation_set.exists():
                data['organisations'] = "%s%s?country=%s" % (base, reverse('api:v2_organisations'), obj.country.iso2_code)
            if obj.country.adminregion_set.exists():
                data['regions'] = "%s%s?country=%s" % (base, reverse('api:v2_regions'), obj.country.iso2_code)
            if obj.country_groups.all().exists():
                data['country_groups'] = "%s%s?country=%s" % (base, reverse('api:v2_country_groups'), obj.country.iso2_code)
        return data
  

class CountryDetailView(CountryMixin, JsonDetailView):
    slug_field = 'country__iso2_code'
    slug_url_kwarg = 'iso2_code'
    http_method_names = ['get', 'options']
    operations = {}
    
    def get_queryset(self):
        return super(CountryDetailView, self).get_queryset().prefetch_related('country', 'email')

    def get_object_data(self, request, obj):
        return super(CountryDetailView, self).get_object_data(request, obj, details=True)


class CountryList(CountryMixin, JsonListView):

    def get_queryset(self):
        qs = super(CountryList, self).get_queryset().filter(is_active=True).prefetch_related('country', 'email')
        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(country__name__icontains=name)
            
        country_group_id = self.request.GET.get('country_group_id', None)
        if country_group_id:
            qs = qs.filter(country_groups__uuid=country_group_id)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed) | Q(country__last_modified__gte=parsed) )

        return qs
