# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DeleteView, DetailView, CreateView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.contrib import messages
from l10n.models import Country
from utils.url import is_safe_url
from sso.views import main
from sso.views.main import FilterItem
from sso.emails.models import EmailForward, Email, EmailAlias
from sso.organisations.models import AdminRegion, Organisation
from sso.views.generic import FormsetsUpdateView, ListView, SearchFilter, ViewChoicesFilter, ViewQuerysetFilter
from sso.organisations.models import OrganisationAddress, OrganisationPhoneNumber
from sso.emails.forms import AdminEmailForwardForm, EmailForwardForm, EmailAliasForm
from sso.organisations.forms import OrganisationCenterForm, OrganisationAddressForm, OrganisationPhoneNumberForm, OrganisationAdminForm

import logging
logger = logging.getLogger(__name__)


def get_last_modified(request, *args, **kwargs):
    center_last_modified = Organisation.objects.latest("last_modified").last_modified
    address_last_modified = OrganisationAddress.objects.latest("last_modified").last_modified
    phonenumber_last_modified = OrganisationPhoneNumber.objects.latest("last_modified").last_modified
    last_modified = max(center_last_modified, address_last_modified, phonenumber_last_modified)
    return last_modified


class OrganisationBaseView(object):
    model = Organisation
    slug_field = slug_url_kwarg = 'uuid'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationBaseView, self).dispatch(request, *args, **kwargs)

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

    def get_context_data(self, **kwargs):
        """
        Insert the return_url into the context dict.
        """
        context = {}
        return_url = self.get_return_url()
        if return_url:
            context['return_url'] = return_url
        
        if self.object and self.request.user.is_authenticated():
            context['has_organisation_access'] = self.request.user.has_organisation_access(self.object.uuid)
        
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
        if not request.user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(OrganisationDeleteView, self).dispatch(request, *args, **kwargs)


# TODO: ensure that the new created center can be edited by the user who created the center
class OrganisationCreateView(OrganisationBaseView, CreateView):
    form_class = OrganisationAdminForm
    template_name_suffix = '_create_form'
    
    def get_success_url(self):
        return reverse('organisations:organisation_update', args=[self.object.uuid])

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.add_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        return super(OrganisationCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super(OrganisationCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


def get_optional_email_inline_formset(request, email, Model, Form, max_num=6, extra=1, queryset=None):
    InlineFormSet = inlineformset_factory(Email, Model, Form, extra=extra, max_num=max_num)
    if not email:
        return None
    if request.method == 'POST':
        formset = InlineFormSet(request.POST, instance=email, queryset=queryset)        
        try:
            # Check if there was a InlineFormSet in the request because
            # InlineFormSet is only in the response when the organisation has an email
            formset.initial_form_count()
        except ValidationError:
            formset = None  # there is no InlineFormSet in the request
    else:
        formset = InlineFormSet(instance=email, queryset=queryset)
    return formset
        

class OrganisationUpdateView(OrganisationBaseView, FormsetsUpdateView):
    form_class = OrganisationCenterForm
    
    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        # additionally check if the user is admin of the organisation       
        if not request.user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(OrganisationUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super(OrganisationUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        if self.request.user.has_perm('organisations.add_organisation'):
            return OrganisationAdminForm
        else:
            return self.form_class
        
    def get_formsets(self):

        address_extra = 0
        phone_number_extra = 1
        
        address_count = self.object.organisationaddress_set.count()
        if address_count == 0: 
            address_extra = 1
        
        AddressInlineFormSet = inlineformset_factory(self.model, OrganisationAddress, OrganisationAddressForm, extra=address_extra, max_num=3)
        PhoneNumberInlineFormSet = inlineformset_factory(self.model, OrganisationPhoneNumber, OrganisationPhoneNumberForm, max_num=6, extra=phone_number_extra)

        if self.request.method == 'POST':
            address_inline_formset = AddressInlineFormSet(self.request.POST, instance=self.object)
            phone_number_inline_formset = PhoneNumberInlineFormSet(self.request.POST, instance=self.object)
        else:           
            address_inline_formset = AddressInlineFormSet(instance=self.object)
            phone_number_inline_formset = PhoneNumberInlineFormSet(instance=self.object)
        
        address_inline_formset.forms += [address_inline_formset.empty_form] 
        phone_number_inline_formset.forms += [phone_number_inline_formset.empty_form]
        formsets = [address_inline_formset, phone_number_inline_formset]
        
        if self.request.method == 'GET' or 'email' not in self.form.changed_data:
            if self.request.user.has_perm('organisations.add_organisation'):
                email_forward_inline_formset = get_optional_email_inline_formset(self.request, self.object.email, 
                                                                                 Model=EmailForward, Form=AdminEmailForwardForm, max_num=10)
            else:
                email_forward_inline_formset = get_optional_email_inline_formset(self.request, self.object.email, 
                                                                                 Model=EmailForward, Form=EmailForwardForm, max_num=10, 
                                                                                 queryset=EmailForward.objects.filter(primary=False))
                
            email_alias_inline_formset = get_optional_email_inline_formset(self.request, self.object.email, 
                                                                           Model=EmailAlias, Form=EmailAliasForm, max_num=6)
            
            if email_forward_inline_formset:
                email_forward_inline_formset.forms += [email_forward_inline_formset.empty_form]
                formsets += [email_forward_inline_formset]
            if email_alias_inline_formset:
                email_alias_inline_formset.forms += [email_alias_inline_formset.empty_form]
                formsets += [email_alias_inline_formset]
        
        return formsets
    

class OrganisationSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__email__icontains']


class CenterTypeFilter(ViewChoicesFilter):
    name = 'center_type'
    choices = Organisation.CENTER_TYPE_CHOICES
    select_text = _('Select Center Type')
    select_all_text = _("All Center Types")


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Centers')), ('2', _('Inactive Centers')))  
    select_text = _('Select active/inactive')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    model = Country
    filter_list = Country.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Select Country')
    select_all_text = _('All Countries')
    all_remove = 'center'
    remove = 'center,app_role,role_profile,p'


class AdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    model = AdminRegion
    select_text = _('Select Region')
    select_all_text = _('All Regions')
    all_remove = 'region,center'
    remove = 'region,center,app_role,role_profile,p'
    

class OrganisationList(ListView):
    template_name = 'organisations/organisation_list.html'
    model = Organisation
    list_display = ['name', 'email', 'google maps', 'country', 'founded']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationList, self).dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        # apply my_organisations filter only for admins
        my_organisations = None
        if self.request.user.is_user_admin:
            my_organisations = self.request.GET.get('my_organisations', '')
        
        if my_organisations:
            self.my_organisations = my_organisations
            qs = self.request.user.get_administrable_organisations()
        else:
            self.my_organisations = None
            qs = super(OrganisationList, self).get_queryset().select_related('country', 'email')
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['name'])
        
        # apply filters
        qs = OrganisationSearchFilter().apply(self, qs) 
        qs = CenterTypeFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        # offer is_active filter only for admins
        if self.request.user.is_organisation_admin:  
            qs = IsActiveFilter().apply(self, qs)
        else:
            qs = qs.filter(is_active=True)
            
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
        
        center_type_filter = CenterTypeFilter().get(self)
        country_filter = CountryFilter().get(self)
        admin_region_filter = AdminRegionFilter().get(self)
        
        filters = [country_filter, admin_region_filter, center_type_filter]
        # is_active filter is only for admins
        if self.request.user.is_organisation_admin:  
            filters.append(IsActiveFilter().get(self))
        
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
