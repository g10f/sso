# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_text
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import ListView, DeleteView, DetailView, CreateView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.contrib import messages

from l10n.models import Country

from sso.views import main
from sso.views.main import FilterItem
from sso.organisations.models import AdminRegion, Organisation
from sso.views.generic import FormsetsUpdateView
from utils.url import is_safe_url
from .models import OrganisationAddress, OrganisationPhoneNumber
from .forms import OrganisationForm, OrganisationAddressForm, OrganisationPhoneNumberForm

import logging
logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_authenticated() and user.is_admin()


def get_last_modified(request, *args, **kwargs):
    center_last_modified = Organisation.objects.latest("last_modified").last_modified
    address_last_modified = OrganisationAddress.objects.latest("last_modified").last_modified
    phonenumber_last_modified = OrganisationPhoneNumber.objects.latest("last_modified").last_modified
    last_modified = max(center_last_modified, address_last_modified, phonenumber_last_modified)
    return last_modified


class OrganisationBaseView(object):
    model = Organisation
    slug_field = slug_url_kwarg = 'uuid'

    def get_return_url(self):
        return_url = self.request.GET.get("return_url")
        if return_url and is_safe_url(return_url):
            return return_url        
        return ""
    
    def get_initial(self):
        initial = self.initial.copy()
        if self.object:  # update view
            initial['google_maps_url'] = self.object.google_maps_url
        return initial           

    def get_form_kwargs(self):
        kwargs = super(OrganisationBaseView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Insert the return_url into the context dict.
        """
        context = {}
        return_url = self.get_return_url()
        if return_url:
            context['return_url'] = return_url
        
        if self.object and self.request.user.is_authenticated():
            context['is_organisation_admin'] = self.request.user.is_organisation_admin(self.object.uuid)
        
        context.update(kwargs)
        return super(OrganisationBaseView, self).get_context_data(**context)


class OrganisationDetailView(OrganisationBaseView, DetailView):
    pass


class MyOrganisationDetailView(OrganisationBaseView, DetailView):
    """
    View of the center the user belongs to.
    """
    template_name = "organisations/my_organisation_detail.html"
    
    def get_object(self, queryset=None):
        return self.request.user.organisations.first()
    

class OrganisationDeleteView(OrganisationBaseView, DeleteView):
    def get_success_url(self):
        return reverse('organisations:organisation_list')

    @method_decorator(permission_required('organisations.delete_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):       
        # additionally check if the user is admin of the organisation       
        if not request.user.is_organisation_admin(kwargs.get('uuid')):
            raise PermissionDenied
        return super(OrganisationDeleteView, self).dispatch(request, *args, **kwargs)


class OrganisationCreateView(OrganisationBaseView, CreateView):
    form_class = OrganisationForm
    template_name_suffix = '_create_form'
    
    def get_success_url(self):
        return reverse('organisations:organisation_update', args=[self.object.uuid])

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.add_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        return super(OrganisationCreateView, self).dispatch(request, *args, **kwargs)


class OrganisationUpdateView(OrganisationBaseView, FormsetsUpdateView):
    form_class = OrganisationForm
    
    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        # additionally check if the user is admin of the organisation       
        if not request.user.is_organisation_admin(kwargs.get('uuid')):
            raise PermissionDenied
        return super(OrganisationUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_formsets(self):
        address_extra = 0
        phonenumber_extra = 1
        
        address_count = self.object.organisationaddress_set.count()
        if address_count == 0: 
            address_extra = 1
        
        AddressInlineFormSet = inlineformset_factory(self.model, OrganisationAddress, OrganisationAddressForm, extra=address_extra, max_num=3)
        PhoneNumberInlineFormSet = inlineformset_factory(self.model, OrganisationPhoneNumber, OrganisationPhoneNumberForm, extra=phonenumber_extra, max_num=6)

        if self.request.method == 'POST':
            address_inline_formset = AddressInlineFormSet(self.request.POST, instance=self.object)
            phonenumber_inline_formset = PhoneNumberInlineFormSet(self.request.POST, instance=self.object)
        else:           
            address_inline_formset = AddressInlineFormSet(instance=self.object)
            phonenumber_inline_formset = PhoneNumberInlineFormSet(instance=self.object)
        
        address_inline_formset.forms += [address_inline_formset.empty_form] 
        phonenumber_inline_formset.forms += [phonenumber_inline_formset.empty_form]
        return [address_inline_formset, phonenumber_inline_formset]

    def get_success_url(self):
        msg = ""
        success_url = ""
        msg_dict = {'name': force_text(self.model._meta.verbose_name), 'obj': force_text(self.object)}
        if "_continue" in self.request.POST:
            msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
            success_url = reverse('organisations:organisation_update', args=[self.object.uuid])
        else:
            msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
            success_url = super(OrganisationUpdateView, self).get_success_url()   
            
        messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
        return success_url    
    

class OrganisationList(ListView):
    template_name = 'organisations/organisation_list.html'
    model = Organisation
    paginate_by = 20
    page_kwarg = main.PAGE_VAR
    list_display = ['name', 'email', 'google maps', 'country', 'founded']
    IS_ACTIVE_CHOICES = (('1', _('Active Centers')), ('2', _('Inactive Centers')))  

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationList, self).dispatch(request, *args, **kwargs)

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
        # apply my_organisations filter only for admins
        my_organisations = None
        if self.request.user.is_admin():
            my_organisations = self.request.GET.get('my_organisations', '')
        
        if my_organisations:
            self.my_organisations = my_organisations
            qs = self.request.user.get_administrable_organisations()
        else:
            self.my_organisations = None
            qs = super(OrganisationList, self).get_queryset().select_related('country')
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['name'])
        # apply search filter
        search_var = self.request.GET.get(main.SEARCH_VAR, '')
        if search_var:
            search_list = search_var.split(' ')
            q = Q()
            for search in search_list:
                q |= Q(name__icontains=search) | Q(email__icontains=search)
            qs = qs.filter(q)
        
        # apply country filter
        country = self.request.GET.get('country', '')
        if country:
            self.country = Country.objects.get(pk=country)
            qs = qs.filter(country__in=[self.country])
        else:
            self.country = None

        # apply admin_region filter
        admin_region = self.request.GET.get('admin_region', '')
        if admin_region:
            self.admin_region = AdminRegion.objects.get(pk=admin_region)
            qs = qs.filter(admin_region__in=[self.admin_region])
        else:
            self.admin_region = None

        # apply center_type filter
        center_type = self.request.GET.get('center_type', '')
        if center_type:
            self.center_type = FilterItem((center_type, dict(Organisation.CENTER_TYPE_CHOICES)[center_type]))
            qs = qs.filter(center_type=center_type)
        else:
            self.center_type = None

        # apply is_active filter only for admins
        if self.request.user.is_admin():
            is_active = self.request.GET.get('is_active', '')
        else:
            is_active = "1"
            
        if is_active:
            self.is_active = FilterItem((is_active, dict(OrganisationList.IS_ACTIVE_CHOICES)[is_active]))
            is_active_filter = True if (is_active == "1") else False
            qs = qs.filter(is_active=is_active_filter)
        else:
            self.is_active = None
            
        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
        
        countries = Country.objects.filter(organisation__isnull=False).distinct()
        admin_regions = AdminRegion.objects.all()
        if len(countries) == 1:
            self.country = countries[0]
            countries = Country.objects.none()

        if len(countries) == 1:
            countries = None
        if len(admin_regions) == 1:
            admin_regions = None
        
        if self.request.user.is_admin():  # offer is_active filter only for admins
            is_active_list = [FilterItem(item) for item in OrganisationList.IS_ACTIVE_CHOICES]
        else:
            is_active_list = None
        center_types = [FilterItem(item) for item in Organisation.CENTER_TYPE_CHOICES]
        filters = [
            {
                'selected': self.country, 'list': countries, 'select_text': _('Select Country'), 'select_all_text': _("All Countries"), 
                'param_name': 'country', 'all_remove': 'region,center', 'remove': 'region,center,app_role,role_profile,p'
            }, {
                'selected': self.admin_region, 'list': admin_regions, 'select_text': _('Select Region'), 'select_all_text': _("All Regions"), 
                'param_name': 'admin_region', 'all_remove': 'center', 'remove': 'center,app_role,role_profile,p'
            }, {
                'selected': self.center_type, 'list': center_types, 'select_text': _('Select Center Type'), 'select_all_text': _("All Center Types"), 
                'param_name': 'center_type', 'all_remove': '', 'remove': 'p'
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
            'my_organisations': getattr(self, 'my_organisations', '')
        }
        context.update(kwargs)
        return super(OrganisationList, self).get_context_data(**context)
