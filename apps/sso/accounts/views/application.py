# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import ListView, DeleteView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.encoding import force_text

from l10n.models import Country

from sso.views import main
from sso.views.main import FilterItem
from sso.accounts.models import ApplicationRole, RoleProfile, User, send_account_created_email  # Region, Organisation, 
from sso.organisations.models import AdminRegion, Organisation
from sso.accounts.forms import UserAddFormExt, UserProfileForm

import logging

logger = logging.getLogger(__name__)


# TODO: refine the permission checks
def is_admin(user):
    return user.is_authenticated() and user.is_admin()
    

class UserDeleteView(DeleteView):
    model = get_user_model()
    success_url = reverse_lazy('accounts:user_list')

    def get_queryset(self):
        # filter the users for who the authenticated user has admin rights
        user = self.request.user
        qs = super(UserDeleteView, self).get_queryset()
        return user.filter_administrable_users(qs)
    
    @method_decorator(user_passes_test(is_admin))
    def dispatch(self, request, *args, **kwargs):
        return super(UserDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDeleteView, self).get_context_data(**kwargs)
        context['cancel_url'] = reverse('accounts:update_user', args=[self.object.uuid])
        return context


class UserList(ListView):
    template_name = 'accounts/application/user_list.html'
    model = get_user_model()
    paginate_by = 20
    page_kwarg = main.PAGE_VAR
    list_display = ['username', 'first_name', 'last_name', 'email', 'last_login', 'date_joined']
    IS_ACTIVE_CHOICES = (('1', _('Active Users')), ('2', _('Inactive Users')))
    
    @method_decorator(user_passes_test(is_admin))
    def dispatch(self, request, *args, **kwargs):
        return super(UserList, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get(main.PAGE_SIZE_VAR, self.paginate_by))
        except ValueError:
            return self.paginate_by

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        user = self.request.user
        qs = super(UserList, self).get_queryset()
        qs = user.filter_administrable_users(qs)
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-last_login'])
        # apply search filter
        search_var = self.request.GET.get(main.SEARCH_VAR, '')
        if search_var:
            search_list = search_var.split(' ')
            q = Q()
            for search in search_list:
                q |= Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search)
            qs = qs.filter(q)
        
        # apply country filter
        country = self.request.GET.get('country', '')
        if country:
            self.country = Country.objects.get(pk=country)
            qs = qs.filter(organisations__country__in=[self.country])
        else:
            self.country = None

        # apply admin_region filter
        admin_region = self.request.GET.get('admin_region', '')
        if admin_region:
            self.admin_region = AdminRegion.objects.get(pk=admin_region)
            qs = qs.filter(organisations__admin_region__in=[self.admin_region])
        else:
            self.admin_region = None

        # apply center filter
        center = self.request.GET.get('center', '')
        if center:
            self.center = Organisation.objects.get(pk=center)
            qs = qs.filter(organisations__in=[self.center])
        else:
            self.center = None
            
        # apply app_role filter
        app_role = self.request.GET.get('app_role', '')
        if app_role:
            self.app_role = ApplicationRole.objects.get(pk=app_role)
            q = Q(application_roles__in=[self.app_role])
            q |= Q(role_profiles__application_roles__in=[self.app_role])
            qs = qs.filter(q)
        else:
            self.app_role = None

        # apply role_profile filter
        role_profile = self.request.GET.get('role_profile', '')
        if role_profile:
            self.role_profile = RoleProfile.objects.get(pk=role_profile)
            q = Q(role_profiles__in=[self.role_profile])
            qs = qs.filter(q)
        else:
            self.role_profile = None

        # apply is_active filter
        is_active = self.request.GET.get('is_active', '1')
        if is_active:
            self.is_active = FilterItem((is_active, dict(UserList.IS_ACTIVE_CHOICES)[is_active]))
            is_active_filter = True if (is_active == "1") else False
            qs = qs.filter(is_active=is_active_filter)
        else:
            self.is_active = None

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
        
        centers = Organisation.objects.none()
        application_roles = user.get_administrable_application_roles()
        role_profiles = user.get_administrable_role_profiles()
        countries = user.get_countries_of_administrable_organisations()
        admin_regions = user.get_administrable_regions()
        if len(countries) == 1:
            self.country = countries[0]
            countries = Country.objects.none()

        if self.country:
            centers = user.get_administrable_organisations().filter(country=self.country)
            if self.admin_region:
                centers = centers.filter(admin_region=self.admin_region)
            application_role_ids = [x.id for x in application_roles]
            if self.center:
                application_roles = ApplicationRole.objects.filter(id__in=application_role_ids, user__organisations__in=[self.center]).select_related().distinct()
                role_profiles = role_profiles.filter(user__organisations__in=[self.center]).distinct()
            else:
                application_roles = ApplicationRole.objects.filter(id__in=application_role_ids, user__organisations__in=centers).select_related().distinct() 
                role_profiles = role_profiles.filter(user__organisations__in=centers).distinct()

        if len(countries) == 1:
            countries = None
        if len(admin_regions) == 1:
            admin_regions = None
        if len(centers) == 1:
            centers = None
        
        is_active_list = [FilterItem(item) for item in UserList.IS_ACTIVE_CHOICES]
        filters = [{
                'selected': self.country, 'list': countries, 'select_text': _('Select Country'), 'select_all_text': _("All Countries"), 
                'param_name': 'country', 'all_remove': 'region,center', 'remove': 'region,center,app_role,role_profile,p'
            }, {
                'selected': self.admin_region, 'list': admin_regions, 'select_text': _('Select Region'), 'select_all_text': _("All Regions"), 
                'param_name': 'admin_region', 'all_remove': 'center', 'remove': 'center,app_role,role_profile,p'
            }, {
                'selected': self.center, 'list': centers, 'select_text': _('Select Center'), 'select_all_text': _("All Centers"), 
                'param_name': 'center', 'all_remove': '', 'remove': 'app_role,p'
            }, {
                'selected': self.role_profile, 'list': role_profiles, 'select_text': _('Select Profile'), 'select_all_text': _("All Profiles"), 
                'param_name': 'role_profile', 'all_remove': '', 'remove': 'p'
            }, {
                'selected': self.app_role, 'list': application_roles, 'select_text': _('Select Role'), 'select_all_text': _("All Roles"), 
                'param_name': 'app_role', 'all_remove': '', 'remove': 'p'
            }, {
                'selected': self.is_active, 'list': is_active_list, 'select_text': _('Select active/inactive'), 'select_all_text': _("All"), 
                'param_name': 'is_active', 'all_remove': '', 'remove': 'p'
            }
        ]
        
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
    
    
@user_passes_test(is_admin)
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

    data = {'form': form,
             'title': _('Add user')}
    return render(request, template, data)


@user_passes_test(is_admin)
def add_user_done(request, uuid, template='accounts/application/add_user_done.html'):
    new_user = get_user_model().objects.get(uuid=uuid)
    data = {'new_user': new_user, 'title': _('Add user')}
    return render(request, template, data)

    
@user_passes_test(is_admin)
def update_user(request, uuid, template='accounts/application/change_user_form.html'):
    #TODO: check if the authenticated user has admin rights for the organisation
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
