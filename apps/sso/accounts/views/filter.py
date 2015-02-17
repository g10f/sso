# -*- coding: utf-8 -*-
import logging

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from l10n.models import Country
from sso.views.generic import SearchFilter, ViewChoicesFilter, ViewQuerysetFilter
from sso.accounts.models import ApplicationRole, RoleProfile
from sso.organisations.models import AdminRegion, Organisation


logger = logging.getLogger(__name__)


class UserSearchFilter(SearchFilter):
    search_names = ['username__icontains', 'first_name__icontains', 'last_name__icontains', 'useremail__email__icontains']


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Users')), ('2', _('Inactive Users')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'organisations__country'
    model = Country
    filter_list = Country.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Country')
    select_all_text = _('All Countries')
    all_remove = 'admin_region,center'
    remove = 'admin_region,center,app_role,role_profile,p'


class AdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    qs_name = 'organisations__admin_region'
    model = AdminRegion
    select_text = _('Region')
    select_all_text = _('All Regions')
    all_remove = 'center'
    remove = 'center,app_role,role_profile,p'


class CenterFilter(ViewQuerysetFilter):
    name = 'center'
    qs_name = 'organisations'
    model = Organisation
    select_text = _('Center')
    select_all_text = _('All Centers')
    remove = 'app_role,p'


class ApplicationRoleFilter(ViewQuerysetFilter):
    name = 'app_role'
    model = ApplicationRole
    select_text = _('Role')
    select_all_text = _('All Roles')

    def apply(self, view, qs, default=''):
        """
        filter with respect to application_roles and role_profiles
        """
        value = self.get_value_from_query_param(view, default)
        if value:
            q = Q(application_roles=value)
            q |= Q(role_profiles__application_roles=value)
            qs = qs.filter(q)
        setattr(view, self.name, value)
        return qs


class RoleProfileFilter(ViewQuerysetFilter):
    name = 'role_profile'
    qs_name = 'role_profiles'
    model = RoleProfile
    select_text = _('Profile')
    select_all_text = _('All Profiles')


########################################################################################
# organisationchange list filter


class OrganisationChangeCountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'organisation__country'
    model = Country
    filter_list = Country.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Country')
    select_all_text = _('All Countries')
    all_remove = 'admin_region'
    remove = 'admin_region,p'


class OrganisationChangeAdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    qs_name = 'organisation__admin_region'
    model = AdminRegion
    select_text = _('Region')
    select_all_text = _('All Regions')
    all_remove = ''
    remove = 'p'




