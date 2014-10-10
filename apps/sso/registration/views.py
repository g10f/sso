# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.template.response import TemplateResponse
from django.views.generic import DeleteView
from django.contrib.auth.decorators import permission_required, login_required
from django.utils.decorators import method_decorator
from l10n.models import Country
from django.utils.encoding import force_text
from django.core.urlresolvers import reverse, reverse_lazy
from sso.views import main
from sso.views.generic import SearchFilter, ViewChoicesFilter, ViewQuerysetFilter
from .models import RegistrationProfile, RegistrationManager, send_user_validated_email
from .forms import RegistrationProfileForm
from .tokens import default_token_generator


class UserRegistrationDeleteView(DeleteView):
    model = get_user_model()
    success_url = reverse_lazy('registration:user_registration_list')

    def get_queryset(self):
        # filter the users for who the authenticated user has admin rights
        qs = super(UserRegistrationDeleteView, self).get_queryset()
        user = self.request.user
        return user.filter_administrable_users(qs)
    
    @method_decorator(login_required)
    @method_decorator(permission_required('registration.change_registrationprofile', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(UserRegistrationDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserRegistrationDeleteView, self).get_context_data(**kwargs)
        context['cancel_url'] = reverse('registration:update_user_registration', args=[self.object.registrationprofile.pk])
        return context
    

class RegistrationSearchFilter(SearchFilter):
    search_names = ['user__username__icontains', 'user__first_name__icontains', 
                    'user__last_name__icontains', 'user__email__icontains']


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'user__organisations__country'
    model = Country
    select_text = _('Country')
    select_all_text = _('All Countries')


class IsVerifiedFilter(ViewChoicesFilter):
    name = 'is_verified'
    qs_name = 'verified_by_user__isnull'
    choices = (('1', _('Verified Users')), ('2', _('Unverified Users')))  
    select_text = _('verified filter')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return False if (value.pk == "1") else True


class CheckBackFilter(ViewChoicesFilter):
    name = 'check_back'
    choices = (('1', _('Check Back Required')), ('2', _('No Check Back Required')))  
    select_text = _('check back filter')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class IsAccessDeniedFilter(ViewChoicesFilter):
    name = 'is_access_denied'
    choices = (('1', _('Access Denied')), ('2', _('Access Not Denied')))  
    select_text = _('access denied filter')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class UserRegistrationList(main.ListView):
    template_name = 'registration/user_registration_list.html'
    model = RegistrationProfile
    paginate_by = 20
    page_kwarg = main.PAGE_VAR
    list_display = ['user', 'email', 'center', 'date_registered', 'verified_by_user', 'check_back', 'is_access_denied']
    
    @method_decorator(login_required)
    @method_decorator(permission_required('registration.change_registrationprofile', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(UserRegistrationList, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get(main.PAGE_SIZE_VAR, self.paginate_by))
        except ValueError:
            return self.paginate_by

    def get_queryset(self):
        qs = super(UserRegistrationList, self).get_queryset().prefetch_related('user__organisations', 'user__organisations__country', 'user__useraddress_set', 'user__useraddress_set__country')\
            .select_related('user', 'user__useraddress__country__printable_name').filter(user__is_active=False, is_validated=True)
        
        # display only users from centers where the logged in user has admin rights
        user = self.request.user
        qs = RegistrationManager.filter_administrable_registrationprofiles(user, qs)
                
        # Set ordering.
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-date_registered'])
        
        # apply filters
        qs = RegistrationSearchFilter().apply(self, qs) 
        qs = CountryFilter().apply(self, qs) 
        qs = CheckBackFilter().apply(self, qs) 
        qs = IsAccessDeniedFilter().apply(self, qs) 
        qs = IsVerifiedFilter().apply(self, qs) 
        
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs
     
    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
        
        # list of centers of registrations where the user has admin rights
        user_organisations = self.request.user.get_administrable_user_organisations().filter(
            user__is_active=False, 
            user__registrationprofile__isnull=False,
            user__registrationprofile__is_validated=True)
        countries = Country.objects.filter(pk__in=user_organisations.values_list('country', flat=True))
        
        country_filter = CountryFilter().get(self, countries)
        is_verified_filter = IsVerifiedFilter().get(self)
        check_back_filter = CheckBackFilter().get(self)
        is_access_denied_filter = IsAccessDeniedFilter().get(self)
        
        filters = [country_filter, is_verified_filter, check_back_filter, is_access_denied_filter]
        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'filters': filters,
        }
        context.update(kwargs)
        return super(UserRegistrationList, self).get_context_data(**context)


@login_required
@permission_required('registration.change_registrationprofile', raise_exception=True)
def update_user_registration(request, pk, template='registration/change_user_registration_form.html'):
    registrationprofile = get_object_or_404(RegistrationProfile, pk=pk)
    if not request.user.has_user_access(registrationprofile.user.uuid):
        raise PermissionDenied
    
    if request.method == 'POST':
        registrationprofile_form = RegistrationProfileForm(request.POST, instance=registrationprofile, request=request)
        if registrationprofile_form.is_valid(): 
            msg = ""
            success_url = ""
            msg_dict = {'name': force_text(get_user_model()._meta.verbose_name), 'obj': force_text(registrationprofile)}         
            if "_continue" in request.POST:
                registrationprofile = registrationprofile_form.save()
                msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
                success_url = reverse('registration:update_user_registration', args=[registrationprofile.pk])
            elif "_save" in request.POST:
                registrationprofile = registrationprofile_form.save()
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
                success_url = reverse('registration:user_registration_list') + "?" + request.GET.urlencode()
            else:
                registrationprofile = registrationprofile_form.save(activate=True)
                msg = _('The %(name)s "%(obj)s" was activated successfully.') % msg_dict
                success_url = reverse('registration:user_registration_list') + "?" + request.GET.urlencode()
            
            messages.add_message(request, level=messages.SUCCESS, message=msg, fail_silently=True)
            return HttpResponseRedirect(success_url)
    else:
        registrationprofile_form = RegistrationProfileForm(instance=registrationprofile, request=request)

    data = {'form': registrationprofile_form, 'title': _('Edit registration')}
    return render(request, template, data)


def validation_confirm(request, uidb64=None, token=None, token_generator=default_token_generator,
                       template='registration/validation_confirm.html'):
    try:
        from django.utils.http import urlsafe_base64_decode
        uid = urlsafe_base64_decode(uidb64)
        profile = RegistrationProfile.objects.get(pk=uid)
    except (ValueError, RegistrationProfile.DoesNotExist):
        profile = None
    
    validlink = False
    if profile is not None:
        if profile.is_validated:
            return redirect('registration:validation_complete')
        elif token_generator.check_token(profile, token):
            validlink = True
            
            if request.method == 'POST':
                profile.is_validated = True
                profile.save()
                send_user_validated_email(profile, request)
                return redirect('registration:validation_complete')
            
    context = {
        'email': profile.user.email if profile else None,
        'validlink': validlink,
    }
    return TemplateResponse(request, template, context)
