import logging

from sorl.thumbnail import get_thumbnail

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.organisations.models import Organisation, get_near_organisations, multiple_associations, \
    is_validation_period_active
from sso.utils.parse import parse_datetime_with_timezone_support
from sso.utils.url import absolute_url, get_base_url

logger = logging.getLogger(__name__)


class OrganisationMixin(object):
    model = Organisation
    api_mappings = getattr(settings, 'SSO_API_MAPPINGS', {})

    def get_object_data(self, request, obj, details=False):
        # TODO: phase out
        def map_address_type(address_type):
            if 'organisation__address__address_type' not in self.api_mappings:
                return address_type
            return self.api_mappings['organisation__address__address_type'].get(address_type, address_type)

        base = get_base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_organisation', kwargs={'uuid': obj.uuid.hex})),
            'id': '%s' % obj.uuid.hex,
            'is_active': obj.is_active,
            'is_live': obj.is_live,
            'is_private': obj.is_private,
            'name': '%s' % obj.name,
            'name_native': '%s' % obj.name_native,
            'slug': '%s' % obj.slug,
            'founded': obj.founded,
            'center_type': obj.center_type,
            'homepage': obj.homepage,
            'google_plus_page': obj.google_plus_page,
            'facebook_page': obj.facebook_page,
            'twitter_page': obj.twitter_page,
            'last_modified': obj.get_last_modified_deep(),
            'is_validation_period_active': is_validation_period_active(obj),
        }
        if multiple_associations():
            data['association'] = {
                '@id': "%s%s" % (base, reverse('api:v2_association', kwargs={'uuid': obj.association.uuid.hex})),
                'name': obj.association.name
            }

        if obj.source_urls:
            data['source_urls'] = obj.source_urls
        if obj.email:
            data['email'] = '%s' % obj.email
        if obj.neighbour_distance:
            data['neighbour_distance'] = "%.1f km" % obj.neighbour_distance
        if obj.transregional_distance:
            data['transregional_distance'] = "%.1f km" % obj.transregional_distance
        if obj.centerid:  # legacy id, should be removed when the resync ist done
            data['centerid'] = obj.centerid
        if obj.timezone:
            data['timezone'] = obj.timezone
            # data['utc_offset'] = localtime(now(), timezone(obj.timezone)).strftime('%z')
        for address in obj.organisationaddress_set.all():
            data['country_code'] = address.country.iso2_code
            break

        if obj.organisation_country is not None:
            data['country'] = {
                'code': obj.organisation_country.country.iso2_code,
                '@id': "%s%s" % (
                    base, reverse('api:v2_country', kwargs={'iso2_code': obj.organisation_country.country.iso2_code})),
            }
        if obj.admin_region is not None:
            data['region'] = {
                'id': obj.admin_region.uuid.hex,
                '@id': "%s%s" % (base, reverse('api:v2_region', kwargs={'uuid': obj.admin_region.uuid.hex})),
            }

        try:
            # if we have a gis query
            data['distance'] = "%.1f km" % obj.distance.km
        except AttributeError:
            pass

        if request.client.is_trustworthy or not obj.is_private:
            if obj.location:
                data['location'] = {'geo': {'latitude': obj.location.y, 'longitude': obj.location.x},
                                    'type': obj.coordinates_type}

        if details:
            if ('users' in request.scopes) and (obj in request.user.get_administrable_user_organisations()):
                data['users'] = "%s%s?org_id=%s" % (base, reverse('api:v2_users'), obj.uuid.hex)

            if request.client.is_trustworthy or not obj.is_private:
                data['addresses'] = {
                    address.uuid.hex: {
                        'address_type': map_address_type(address.address_type),
                        'careof': address.careof,
                        'name': address.addressee,
                        'street_address': address.street_address,
                        'city': address.city,
                        'city_native': address.city_native,
                        'postal_code': address.postal_code,
                        'country': address.country.iso2_code,
                        'region': address.region,
                        'primary': address.primary
                    } for address in obj.organisationaddress_set.all()
                }
            data['phone_numbers'] = {
                phone_number.uuid.hex: {
                    'phone_type': phone_number.phone_type,
                    'phone': phone_number.phone,
                    'primary': phone_number.primary
                } for phone_number in obj.organisationphonenumber_set.all()
            }
            data['pictures'] = {
                picture.uuid.hex: {
                    'title': picture.title,
                    'description': picture.description,
                    'order': picture.order,
                    'url': absolute_url(request, picture.picture.url),
                    '30x30': absolute_url(request, get_thumbnail(picture.picture, "30x30", crop="center").url),
                    '60x60': absolute_url(request, get_thumbnail(picture.picture, "60x60", crop="center").url),
                    '120x120': absolute_url(request, get_thumbnail(picture.picture, "120x120", crop="center").url),
                    '240x240': absolute_url(request, get_thumbnail(picture.picture, "240x240", crop="center").url),
                    '480x480': absolute_url(request, get_thumbnail(picture.picture, "480x480", crop="center").url),
                } for picture in obj.organisationpicture_set.all()
            }

        return data


class OrganisationDetailView(OrganisationMixin, JsonDetailView):
    http_method_names = ['get', 'options']
    operations = {}

    def get_queryset(self):
        return super(OrganisationDetailView, self).get_queryset().prefetch_related(
            'organisation_country__country', 'email', 'organisationaddress_set', 'organisationphonenumber_set',
            'organisationpicture_set')

    def get_object_data(self, request, obj):
        return super(OrganisationDetailView, self).get_object_data(request, obj, details=True)

    def delete_object(self, request, obj):
        obj.is_active = False
        obj.save()


class OrganisationList(OrganisationMixin, JsonListView):
    # TODO: caching
    def get_queryset(self):
        qs = super(OrganisationList, self).get_queryset().prefetch_related(
            'organisation_country__country', 'admin_region', 'email', 'organisationaddress_set',
            'organisationaddress_set__country',
            'association', 'organisationphonenumber_set', 'organisationpicture_set').distinct()

        is_live = self.request.GET.get('is_live', 'True')
        if is_live in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']:
            qs = qs.filter(is_live=True)
        elif is_live in ['False', 'false', '0', 'no', 'No', 'N', 'n']:
            qs = qs.filter(is_live=False)

        is_active = self.request.GET.get('is_active', None)
        if is_active in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']:
            qs = qs.filter(is_active=True)
        elif is_active in ['False', 'false', '0', 'no', 'No', 'N', 'n']:
            qs = qs.filter(is_active=False)

        with_unofficial = self.request.GET.get('with_unofficial', 'False')
        if with_unofficial not in ['True', 'true', '1', 'yes', 'Yes', 'Y', 'y']:
            qs = qs.exclude(center_type='4')  # exclude Contact

        org_type = self.request.GET.get('org_type', None)
        if org_type is not None:
            qs = qs.filter(center_type=org_type)

        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(Q(name__icontains=name) | Q(name_native__icontains=name))

        association_id = self.request.GET.get('association_id', None)
        if association_id:
            qs = qs.filter(association__uuid=association_id)

        country_group_id = self.request.GET.get('country_group_id', None)
        if country_group_id:
            qs = qs.filter(organisation_country__country_groups__uuid=country_group_id)

        country = self.request.GET.get('country', None)
        if country:
            qs = qs.filter(organisation_country__country__iso2_code__iexact=country)

        country_code = self.request.GET.get('country_code', None)
        if country_code:
            qs = qs.filter(organisationaddress__country__iso2_code__iexact=country_code)

        region_id = self.request.GET.get('region_id', None)
        if region_id:
            qs = qs.filter(admin_region__uuid=region_id)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed) | Q(organisationaddress__last_modified__gte=parsed) | Q(
                organisationphonenumber__last_modified__gte=parsed)
                           | Q(organisationpicture__last_modified__gte=parsed))

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
