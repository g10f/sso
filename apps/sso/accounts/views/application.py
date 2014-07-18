# -*- coding: utf-8 -*-
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DeleteView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from l10n.models import Country
from sso.views import main
from sso.views.generic import ListView, SearchFilter, ViewChoicesFilter, ViewQuerysetFilter
from sso.accounts.models import ApplicationRole, RoleProfile, User, send_account_created_email 
from sso.organisations.models import AdminRegion, Organisation
from sso.accounts.forms import UserAddFormExt, UserProfileForm

import logging

logger = logging.getLogger(__name__)
    

class UserDeleteView(DeleteView):
    slug_field = slug_url_kwarg = 'uuid'
    model = get_user_model()
    success_url = reverse_lazy('accounts:user_list')
    
    @method_decorator(login_required)
    @method_decorator(permission_required('accounts.delete_user', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the user       
        if not request.user.has_user_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(UserDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDeleteView, self).get_context_data(**kwargs)
        context['cancel_url'] = reverse('accounts:update_user', args=[self.object.uuid])
        return context


class UserSearchFilter(SearchFilter):
    search_names = ['username__icontains', 'first_name__icontains', 'last_name__icontains', 'email__icontains']


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Users')), ('2', _('Inactive Users')))
    select_text = _('Select active/inactive')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'organisations__country'
    model = Country
    filter_list = Country.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Select Country')
    select_all_text = _('All Countries')
    all_remove = 'region,center'
    remove = 'region,center,app_role,role_profile,p'


class AdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    qs_name = 'organisations__admin_region'
    model = AdminRegion
    select_text = _('Select Region')
    select_all_text = _('All Regions')
    all_remove = 'center'
    remove = 'center,app_role,role_profile,p'


class CenterFilter(ViewQuerysetFilter):
    name = 'center'
    qs_name = 'organisations'
    model = Organisation
    select_text = _('Select Center')
    select_all_text = _('All Centers')
    remove = 'app_role,p'


class ApplicationRoleFilter(ViewQuerysetFilter):
    name = 'app_role'
    model = ApplicationRole
    select_text = _('Select Role')
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
    select_text = _('Select Profile')
    select_all_text = _('All Profiles')


class UserList(ListView):
    template_name = 'accounts/application/user_list.html'
    model = get_user_model()
    list_display = ['username', 'first_name', 'last_name', 'email', 'last_login', 'date_joined']
    IS_ACTIVE_CHOICES = (('1', _('Active Users')), ('2', _('Inactive Users')))
    
    @method_decorator(login_required)
    @method_decorator(permission_required('accounts.change_user', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(UserList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user
        qs = super(UserList, self).get_queryset()
        qs = user.filter_administrable_users(qs)
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-last_login'])
        # apply filters
        qs = UserSearchFilter().apply(self, qs) 
        qs = CountryFilter().apply(self, qs) 
        qs = AdminRegionFilter().apply(self, qs) 
        qs = CenterFilter().apply(self, qs) 
        qs = ApplicationRoleFilter().apply(self, qs) 
        qs = RoleProfileFilter().apply(self, qs) 
        qs = IsActiveFilter().apply(self, qs, default='1') 
        
        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        user = self.request.user
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
        
        countries = user.get_administrable_user_countries()
        country_filter = CountryFilter().get(self, countries)

        centers = Organisation.objects.none()
        application_roles = user.get_administrable_application_roles()
        role_profiles = user.get_administrable_role_profiles()
        admin_regions = user.get_administrable_user_regions()

        if self.country:
            centers = user.get_administrable_user_organisations().filter(country=self.country)
            if self.admin_region:
                centers = centers.filter(admin_region=self.admin_region)
            if self.center:
                application_roles = application_roles.filter(user__organisations__in=[self.center]).distinct() 
                role_profiles = role_profiles.filter(user__organisations__in=[self.center]).distinct()
            else:
                application_roles = application_roles.filter(user__organisations__in=centers).distinct() 
                role_profiles = role_profiles.filter(user__organisations__in=centers).distinct()
                
        admin_region_filter = AdminRegionFilter().get(self, admin_regions)
        center_filter = CenterFilter().get(self, centers)
        application_role_filter = ApplicationRoleFilter().get(self, application_roles)
        is_active_filter = IsActiveFilter().get(self)
        role_profile_filter = RoleProfileFilter().get(self, role_profiles)

        filters = [country_filter, admin_region_filter, center_filter, role_profile_filter, application_role_filter, is_active_filter]        
        
        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
            'is_active': self.is_active       
        }
        context.update(kwargs)
        return super(UserList, self).get_context_data(**context)
    
    
@login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user(request, template='accounts/application/add_user_form.html'):
    if request.method == 'POST':
        form = UserAddFormExt(request.user, request.POST)
        if form.is_valid():
            user = form.save()                
            send_account_created_email(user, request)
            
            return HttpResponseRedirect(reverse('accounts:add_user_done', args=[user.uuid]))
    else:
        default_role_profile = User.get_default_role_profile()
        form = UserAddFormExt(request.user, initial={'role_profiles': [default_role_profile]})

    data = {'form': form, 'title': _('Add user')}
    return render(request, template, data)


@login_required
@permission_required('accounts.add_user', raise_exception=True)
def add_user_done(request, uuid, template='accounts/application/add_user_done.html'):
    new_user = get_user_model().objects.get(uuid=uuid)
    data = {'new_user': new_user, 'title': _('Add user')}
    return render(request, template, data)

    
@login_required
@permission_required('accounts.change_user', raise_exception=True)
def update_user(request, uuid, template='accounts/application/change_user_form.html'):
    if not request.user.has_user_access(uuid):
        raise PermissionDenied
    user = get_object_or_404(get_user_model(), uuid=uuid)
    
    if request.method == 'POST':
        userprofile_form = UserProfileForm(request.POST, instance=user, request=request)
        if userprofile_form.is_valid():
            success_url = ""
            user = userprofile_form.save()
            msg_dict = {'name': force_text(get_user_model()._meta.verbose_name), 'obj': force_text(user)}
            if "_addanother" in request.POST:
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may add another %(name)s below.') % msg_dict
                success_url = reverse('accounts:add_user')
            elif "_continue" in request.POST:
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
                success_url = reverse('accounts:update_user', args=[user.uuid])
            else:
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
                success_url = reverse('accounts:user_list') + "?" + request.GET.urlencode()
            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)

    else:
        userprofile_form = UserProfileForm(instance=user, request=request)

    data = {'form': userprofile_form, 'title': _('Change user')}
    return render(request, template, data)
