# -*- coding: utf-8 -*-
import logging

from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_text
from sso.accounts.models import User
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.organisations.models import CountryGroup, OrganisationCountry, Organisation, AdminRegion
from sso.utils.parse import parse_datetime_with_timezone_support
from sso.utils.url import base_url

logger = logging.getLogger(__name__)


class CountryGroupMixin(object):
    model = CountryGroup

    def get_object_data(self, request, obj, details=False):
        base = base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_country_group', kwargs={'uuid': obj.uuid.hex})),
            'id': u'%s' % obj.uuid.hex,
            'name': u'%s' % force_text(obj),
            'homepage': obj.homepage,
            'last_modified': obj.last_modified,
        }
        if obj.email:
            data['email'] = u'%s' % obj.email
        if details:
            if 'users' in request.scopes:
                users = User.objects.filter(organisations__organisation_country__country_groups=obj)
                users = request.user.filter_administrable_users(users)
                if users.exists():
                    data['users'] = "%s%s?country_group_id=%s" % (base, reverse('api:v2_users'), obj.uuid.hex)
            
            if Organisation.objects.filter(organisation_country__country_groups=obj).exists():
                data['organisations'] = "%s%s?country_group_id=%s" % (base, reverse('api:v2_organisations'), obj.uuid.hex)
            if AdminRegion.objects.filter(organisation_country__country_groups=obj).exists():
                data['regions'] = "%s%s?country_group_id=%s" % (base, reverse('api:v2_regions'), obj.uuid.hex)
            if OrganisationCountry.objects.filter(country_groups=obj).exists():
                data['countries'] = "%s%s?country_group_id=%s" % (base, reverse('api:v2_countries'), obj.uuid.hex)
        return data


class CountryGroupDetailView(CountryGroupMixin, JsonDetailView):
    http_method_names = ['get', 'options']
    operations = {}
    
    def get_queryset(self):
        return super(CountryGroupDetailView, self).get_queryset().prefetch_related('email')

    def get_object_data(self, request, obj):
        return super(CountryGroupDetailView, self).get_object_data(request, obj, details=True)


class CountryGroupList(CountryGroupMixin, JsonListView):

    def get_queryset(self):
        qs = super(CountryGroupList, self).get_queryset().prefetch_related('email')
        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(name__icontains=name)

        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(countries__country__iso2_code__iexact=country)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed))

        return qs
