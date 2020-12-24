import logging

from django.utils.translation import gettext_lazy as _
from sso.organisations.models import AdminRegion, OrganisationCountry
from sso.views.generic import SearchFilter, ViewQuerysetFilter

logger = logging.getLogger(__name__)


class AccessRequestCountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'user__organisations__organisation_country'
    model = OrganisationCountry
    filter_list = OrganisationCountry.objects.filter(is_active=True).select_related('country')
    select_text = _('Country')
    select_all_text = _('All Countries')
    all_remove = 'admin_region'
    remove = 'admin_region,p'


class AccessRequestAdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    qs_name = 'user__organisations__admin_region'
    model = AdminRegion
    select_text = _('Region')
    select_all_text = _('All Regions')
    all_remove = ''
    remove = 'p'
