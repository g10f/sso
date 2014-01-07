# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import ListView, DeleteView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.encoding import force_text
from l10n.models import Country
from sso.views import main
from sso.accounts.models import Region, Organisation, ApplicationRole, RoleProfile, send_account_created_email
from sso.accounts.forms import UserAddFormExt, UserProfileForm


def has_permission(user):
    return user.is_authenticated() and user.can_add_users
    

class UserDeleteView(DeleteView):
    model = get_user_model()
    success_url = reverse_lazy('accounts:user_list')

    def get_queryset(self):
        # filter the users for who the authenticated user has admin rights
        user = self.request.user
        qs = super(UserDeleteView, self).get_queryset()
        return user.filter_administrable_users(qs)
    
    @method_decorator(user_passes_test(has_permission))
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
    
    @method_decorator(user_passes_test(has_permission))
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
            self.country = Country.objects.get(iso2_code=country)
            qs = qs.filter(organisations__iso2_code__in=[self.country.iso2_code])
        else:
            self.country = None

        # apply region filter
        region = self.request.GET.get('region', '')
        if region:
            self.region = Region.objects.get(pk=region)
            qs = qs.filter(organisations__region__in=[self.region])
        else:
            self.region = None

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
        is_active = self.request.GET.get('is_active', '')
        if is_active:
            self.is_active = is_active
            is_active_filter = True if (is_active == "True") else False
            qs = qs.filter(is_active=is_active_filter)
        else:
            self.is_active = None

        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        user = self.request.user
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
        
        regions = Region.objects.none()
        centers = Organisation.objects.none()
        application_roles = user.get_administrable_application_roles()
        role_profiles = user.get_administrable_role_profiles()
        countries = user.get_countries_of_administrable_organisations()
        if len(countries) == 1:
            self.country = countries[0]
            countries = Country.objects.none()

        if self.country:
            regions = Region.objects.filter(organisation__iso2_code=self.country.iso2_code).distinct()
            centers = user.get_administrable_organisations().filter(iso2_code=self.country.iso2_code)
            if self.region:
                centers = centers.filter(region=self.region)
            
            if self.center:
                application_roles = application_roles.filter(user__organisations__in=[self.center]).distinct()
                role_profiles = role_profiles.filter(user__organisations__in=[self.center]).distinct()
            else:
                application_roles = application_roles.filter(user__organisations__in=centers).distinct()
                role_profiles = role_profiles.filter(user__organisations__in=centers).distinct()

        if len(countries) == 1:
            countries = None
        if len(regions) == 1:
            regions = None
        if len(centers) == 1:
            centers = None
        
        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'countries': countries,
            'country': self.country,
            'regions': regions,
            'region': self.region,
            'centers': centers,
            'center': self.center,
            'app_roles': application_roles,
            'app_role': self.app_role,
            'role_profiles': role_profiles,
            'role_profile': self.role_profile,
            'is_active': self.is_active       
        }
        context.update(kwargs)
        return super(UserList, self).get_context_data(**context)
    
    
@user_passes_test(has_permission)
def add_user(request, template='accounts/application/add_user_form.html'):
    if request.method == 'POST':
        form = UserAddFormExt(request.user, request.POST)
        if form.is_valid():
            user = form.save()                
            send_account_created_email(user, request)
            
            return HttpResponseRedirect(reverse('accounts:add_user_done', args=[user.uuid]))
    else:
        form = UserAddFormExt(request.user)

    data = {'form': form,
             'title': _('Add user')}
    return render(request, template, data)


@user_passes_test(has_permission)
def add_user_done(request, uuid, template='accounts/application/add_user_done.html'):
    new_user = get_user_model().objects.get(uuid=uuid)
    data = {'new_user': new_user, 'title': _('Add user')}
    return render(request, template, data)

    
@user_passes_test(has_permission)
def update_user(request, uuid, template='accounts/application/change_user_form.html'):
    #TODO: check if the authenticated user has admin rights for the organisation
    user = get_object_or_404(get_user_model(), uuid=uuid)
    
    if request.method == 'POST':
        userprofile_form = UserProfileForm(request.POST, instance=user, request=request)
        if userprofile_form.is_valid():
            user = userprofile_form.save()

            if "_addanother" in request.POST:
                message = _('The user "%(obj)s" was changed successfully. You may add another user below.') % {'obj': force_text(user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('accounts:add_user'))
            elif "_continue" in request.POST:
                message = _('The user "%(obj)s" was changed successfully. You may edit it again below.') % {'obj': force_text(user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('accounts:update_user', args=[user.uuid]))
            else:
                message = _('The user "%(obj)s" was changed successfully.') % {'obj': force_text(user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('accounts:user_list') + "?" + request.GET.urlencode())
    else:
        userprofile_form = UserProfileForm(instance=user, request=request)

    data = {'form': userprofile_form, 'title': _('Change user')}
    return render(request, template, data)
