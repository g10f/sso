import logging

from django.db.models import Q
from django.urls import reverse
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.organisations.models import AdminRegion
from sso.utils.parse import parse_datetime_with_timezone_support
from sso.utils.url import get_base_url

logger = logging.getLogger(__name__)


class RegionMixin(object):
    model = AdminRegion

    def get_object_data(self, request, obj, details=False):
        base = get_base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_region', kwargs={'uuid': obj.uuid.hex})),
            'id': '%s' % obj.uuid.hex,
            'name': '%s' % obj.name,
            'slug': '%s' % obj.slug,
            'homepage': obj.homepage,
            'last_modified': obj.last_modified,
            'country': {
                'code': obj.organisation_country.country.iso2_code,
                '@id': "%s%s" % (
                    base, reverse('api:v2_country', kwargs={'iso2_code': obj.organisation_country.country.iso2_code})),
            }
        }
        if obj.email:
            data['email'] = '%s' % obj.email
        if details:
            if ('users' in request.scopes) and (obj in request.user.get_administrable_user_regions()):
                data['users'] = "%s%s?region_id=%s" % (base, reverse('api:v2_users'), obj.uuid.hex)
            if obj.organisation_set.exists():
                data['organisations'] = "%s%s?region_id=%s" % (base, reverse('api:v2_organisations'), obj.uuid.hex)

        return data


class RegionDetailView(RegionMixin, JsonDetailView):
    http_method_names = ['get', 'options']
    operations = {}

    def get_queryset(self):
        return super().get_queryset().prefetch_related('organisation_country__country', 'email')

    def get_object_data(self, request, obj):
        return super().get_object_data(request, obj, details=True)


class RegionList(RegionMixin, JsonListView):

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True).prefetch_related(
            'organisation_country__country', 'email')
        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(name__icontains=name)

        association_id = self.request.GET.get('association_id', None)
        if association_id:
            qs = qs.filter(organisation_country__association__uuid=association_id)

        country_group_id = self.request.GET.get('country_group_id', None)
        if country_group_id:
            qs = qs.filter(organisation_country__country_groups__uuid=country_group_id)

        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(organisation_country__country__iso2_code__iexact=country)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed))

        return qs
