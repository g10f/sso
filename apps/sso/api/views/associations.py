import logging

from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_text
from sso.accounts.models import User
from sso.api.views.generic import JsonListView, JsonDetailView
from sso.organisations.models import Association, OrganisationCountry, Organisation, AdminRegion
from sso.utils.parse import parse_datetime_with_timezone_support
from sso.utils.url import get_base_url

logger = logging.getLogger(__name__)


class AssociationMixin(object):
    model = Association

    def get_object_data(self, request, obj, details=False):
        base = get_base_url(request)
        data = {
            '@id': "%s%s" % (base, reverse('api:v2_association', kwargs={'uuid': obj.uuid.hex})),
            'id': '%s' % obj.uuid.hex,
            'name': '%s' % force_text(obj),
            'homepage': obj.homepage,
            'last_modified': obj.last_modified,
            'is_active': obj.is_active,
        }
        if obj.email_domain:
            data['email_domain'] = '%s' % obj.email_domain
        if details:
            if 'users' in request.scopes:
                users = User.objects.filter(organisations__association=obj)
                users = request.user.filter_administrable_users(users)
                if users.exists():
                    data['users'] = "%s%s?association_id=%s" % (base, reverse('api:v2_users'), obj.uuid.hex)

            if Organisation.objects.filter(association=obj).exists():
                data['organisations'] = "%s%s?association_id=%s" % (base, reverse('api:v2_organisations'), obj.uuid.hex)
            if AdminRegion.objects.filter(organisation_country__association=obj).exists():
                data['regions'] = "%s%s?association_id=%s" % (base, reverse('api:v2_regions'), obj.uuid.hex)
            if OrganisationCountry.objects.filter(association=obj).exists():
                data['countries'] = "%s%s?association_id=%s" % (base, reverse('api:v2_countries'), obj.uuid.hex)
        return data


class AssociationDetailView(AssociationMixin, JsonDetailView):
    http_method_names = ['get', 'options']
    operations = {}

    def get_object_data(self, request, obj):
        return super(AssociationDetailView, self).get_object_data(request, obj, details=True)


class AssociationList(AssociationMixin, JsonListView):

    def get_queryset(self):
        qs = super(AssociationList, self).get_queryset()
        name = self.request.GET.get('q', None)
        if name:
            qs = qs.filter(name__icontains=name)

        modified_since = self.request.GET.get('modified_since', None)
        if modified_since:  # parse modified_since
            parsed = parse_datetime_with_timezone_support(modified_since)
            if parsed is None:
                raise ValueError("can not parse %s" % modified_since)
            qs = qs.filter(Q(last_modified__gte=parsed))

        return qs
