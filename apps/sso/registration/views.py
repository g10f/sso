
#from django.conf import settings
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.translation import ugettext_lazy as _
#from django.db import transaction
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import get_user_model
#from django.contrib.sites.models import get_current_site
from django.template.response import TemplateResponse
from django.views.generic import DeleteView  # , ListView
from django.db.models import Q
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from l10n.models import Country
from django.utils.encoding import force_text
from django.core.urlresolvers import reverse, reverse_lazy

from sso.views import main
from .models import RegistrationProfile, RegistrationManager, send_user_validated_email  # , send_validation_email
from .forms import RegistrationProfileForm  # ,UserSelfRegistrationForm
from .tokens import default_token_generator
#from . import default_username_generator

def has_permission(user):
    return user.is_authenticated() and user.has_perm('registration.change_registrationprofile')


class UserRegistrationDeleteView(DeleteView):
    model = get_user_model()
    success_url = reverse_lazy('registration:user_registration_list')

    def get_queryset(self):
        # filter the users for who the authenticated user has admin rights
        qs = super(UserRegistrationDeleteView, self).get_queryset()
        user = self.request.user
        return user.filter_administrable_users(qs)
    
    @method_decorator(user_passes_test(has_permission))
    def dispatch(self, request, *args, **kwargs):
        return super(UserRegistrationDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserRegistrationDeleteView, self).get_context_data(**kwargs)
        context['cancel_url'] = reverse('registration:update_user_registration', args=[self.object.registrationprofile.pk])
        return context
    
    
class UserRegistrationList(main.ListView):
    template_name = 'registration/user_registration_list.html'
    model = RegistrationProfile
    paginate_by = 20
    page_kwarg = main.PAGE_VAR
    list_display = ['user', 'email', 'center', 'date_registered', 'verified_by_user', 'check_back', 'is_access_denied']
    
    @method_decorator(user_passes_test(has_permission))
    def dispatch(self, request, *args, **kwargs):
        return super(UserRegistrationList, self).dispatch(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        try:
            return int(self.request.GET.get(main.PAGE_SIZE_VAR, self.paginate_by))
        except ValueError:
            return self.paginate_by

    def get_queryset(self):
        qs = super(UserRegistrationList, self).get_queryset().prefetch_related('user__organisations', 'user__useraddress_set', 'user__useraddress_set__country')\
                    .select_related('user', 'user__useraddress__country__printable_name').filter(user__is_active=False, is_validated=True)
        
        # display only users from centers where the logged in user has admin rights
        user = self.request.user
        qs = RegistrationManager.filter_administrable_registrationprofiles(user, qs)
                
        # Set ordering.
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['-date_registered'])
        
        # apply search filter
        search_var = self.request.GET.get(main.SEARCH_VAR, '')
        if search_var:
            search_list = search_var.split(' ')
            q = Q()
            for search in search_list:
                q |= Q(user__username__icontains=search) | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) | Q(user__email__icontains=search)
            qs = qs.filter(q)
                
        # apply country filter
        country = self.request.GET.get('country', '')
        if country:
            self.country = Country.objects.get(iso2_code=country)
            qs = qs.filter(user__organisations__country__in=[self.country])
        else:
            self.country = None
           
        # apply is_verified filter
        is_verified = self.request.GET.get('is_verified', '')
        if is_verified:
            self.is_verified = is_verified
            is_verified_filter = True if (is_verified == "True") else False
            qs = qs.filter(verified_by_user__isnull=not is_verified_filter)
        else:
            self.is_verified = None
               
        # apply check_back filter
        qs = self.apply_binary_filter(qs, 'check_back')

        # apply is_access_denied filter
        qs = self.apply_binary_filter(qs, 'is_access_denied', 'False')
        
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
        user_organisations = self.request.user.get_administrable_organisations().filter(
                                    user__is_active=False, 
                                    user__registrationprofile__isnull=False,
                                    user__registrationprofile__is_validated=True)
        countries = Country.objects.filter(pk__in=user_organisations.values_list('country', flat=True))
        if len(countries) == 1:
            self.country = countries[0]
            countries = Country.objects.none()
        
        context = {
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'search_var': main.SEARCH_VAR,
            'page_var': main.PAGE_VAR,
            'query': self.request.GET.get(main.SEARCH_VAR, ''),
            'cl': self.cl,
            'countries': countries,
            'country': self.country,
            'is_verified': self.is_verified,   
            'check_back': self.check_back, 
            'is_access_denied': self.is_access_denied      
        }
        context.update(kwargs)
        return super(UserRegistrationList, self).get_context_data(**context)
 

@user_passes_test(has_permission)
def update_user_registration(request, pk, template='registration/change_user_registration_form.html'):
    registrationprofile = get_object_or_404(RegistrationProfile, pk=pk)
    
    if request.method == 'POST':
        registrationprofile_form = RegistrationProfileForm(request.POST, instance=registrationprofile, request=request)
        if registrationprofile_form.is_valid(): 
            if "_continue" in request.POST:
                registrationprofile = registrationprofile_form.save()
                message = _('The user "%(obj)s" was changed successfully. You may edit it again below.') % {'obj': force_text(registrationprofile.user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('registration:update_user_registration', args=[registrationprofile.pk]))
            elif "_save" in request.POST:
                registrationprofile = registrationprofile_form.save()
                message = _('The user "%(obj)s" was changed successfully.') % {'obj': force_text(registrationprofile.user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('registration:user_registration_list') + "?" + request.GET.urlencode())
            else:
                registrationprofile = registrationprofile_form.save(activate=True)
                message = _('The user "%(obj)s" was activated successfully.') % {'obj': force_text(registrationprofile.user)}
                messages.add_message(request, level=messages.INFO, message=message, fail_silently=True)
                return HttpResponseRedirect(reverse('registration:user_registration_list') + "?" + request.GET.urlencode())
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

    if profile is not None and token_generator.check_token(profile, token):
        validlink = True
        if request.method == 'POST':
            profile.is_validated = True
            profile.save()
            send_user_validated_email(profile, request)
            return redirect('registration:validation_complete')
    else:
        validlink = False
            
    context = {
        'email': profile.user.email if profile else None,
        'validlink': validlink,
    }
    return TemplateResponse(request, template, context)


"""
@transaction.atomic
def register(request, username_generator=default_username_generator, form_cls=UserSelfRegistrationForm, template='registration/registration_form.html'):
    
    if not settings.REGISTRATION.get('OPEN', True):
        return redirect('registration:registration_disallowed')

    if request.method == 'POST':
        form = form_cls(request.POST)
        
        if form.is_valid():
            registration_profile = form.save(username_generator)
            send_validation_email(registration_profile, request)
                 
            return redirect('registration:registration_done')
    else:
        form = form_cls()
    
    site_name = settings.SSO_CUSTOM['SITE_NAME']
    data = {
            'site_name': site_name,
            'form': form, 
            'title': _('User registration')}
    return render(request, template, data)
"""
