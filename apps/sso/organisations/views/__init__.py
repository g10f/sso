# -*- coding: utf-8 -*-
import csv
import logging

from django.utils.six.moves.urllib.parse import urlunsplit
from django.http.response import HttpResponse
from django.contrib import messages
from django.utils.encoding import force_text
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DeleteView, DetailView, CreateView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.forms.models import inlineformset_factory
from l10n.models import Country
from sso.views import main
from sso.emails.models import EmailForward, Email, EmailAlias
from sso.organisations.models import AdminRegion, Organisation, OrganisationPicture
from sso.views.generic import FormsetsUpdateView, ListView, SearchFilter, ViewChoicesFilter, ViewQuerysetFilter, ViewButtonFilter
from sso.organisations.models import OrganisationAddress, OrganisationPhoneNumber, get_near_organisations
from sso.emails.forms import AdminEmailForwardInlineForm, EmailForwardInlineForm, EmailAliasInlineForm
from sso.organisations.forms import OrganisationAddressForm, OrganisationPhoneNumberForm, OrganisationCountryAdminForm, \
    OrganisationRegionAdminForm, OrganisationCenterAdminForm, OrganisationRegionAdminCreateForm, OrganisationCountryAdminCreateForm, OrganisationPictureForm
from sso.forms.helpers import get_optional_inline_formset
from sso.utils.url import get_safe_redirect_uri
from sso.utils.ucsv import UnicodeWriter
from sso.oauth2.models import allowed_hosts

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

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        if self.object and self.request.user.is_authenticated():
            context['has_organisation_access'] = self.request.user.has_organisation_access(self.object.uuid)
        
        context.update(kwargs)
        return super(OrganisationBaseView, self).get_context_data(**context)

    def get_success_url(self):
        msg_dict = {'name': force_text(self.model._meta.verbose_name), 'obj': force_text(self.object)}
        if "_continue" in self.request.POST:
            msg = _('The %(name)s "%(obj)s" was changed successfully. You may edit it again below.') % msg_dict
            success_url = urlunsplit(('', '', self.request.path, self.request.GET.urlencode(safe='/'), ''))
            messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)
        else:
            redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
            if redirect_uri:
                success_url = redirect_uri
            else:
                msg = _('The %(name)s "%(obj)s" was changed successfully.') % msg_dict
                success_url = super(FormsetsUpdateView, self).get_success_url()
                messages.add_message(self.request, level=messages.SUCCESS, message=msg, fail_silently=True)

        return success_url


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

    def delete(self, request, *args, **kwargs):
        """
        delete the organisation and email object then
        redirects to the success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        email = self.object.email
        self.object.delete()
        
        if email:
            email.delete() 
        
        return HttpResponseRedirect(success_url)


class OrganisationCreateView(OrganisationBaseView, CreateView):
    template_name_suffix = '_create_form'
    
    def get_success_url(self):
        return urlunsplit(('', '', reverse('organisations:organisation_update', args=[self.object.uuid.hex]), self.request.GET.urlencode(safe='/'), ''))

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

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        user = self.request.user
        if user.get_assignable_organisation_countries().exists():
            return OrganisationCountryAdminCreateForm
        else:
            return OrganisationRegionAdminCreateForm


class OrganisationPictureUpdateView(OrganisationBaseView, FormsetsUpdateView):
    template_name_suffix = '_picture_update_form'
    fields = []

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the organisation
        user = request.user
        if not user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied

        return super(OrganisationPictureUpdateView, self).dispatch(request, *args, **kwargs)

    def get_formsets(self):

        picture_number_extra = 1
        PictureInlineFormSet = inlineformset_factory(self.model, OrganisationPicture, OrganisationPictureForm, extra=picture_number_extra, max_num=3)

        if self.request.method == 'POST':
            picture_inline_formset = PictureInlineFormSet(self.request.POST, files=self.request.FILES, instance=self.object)
        else:
            picture_inline_formset = PictureInlineFormSet(instance=self.object)

        picture_inline_formset.forms += [picture_inline_formset.empty_form]
        return [picture_inline_formset]


class OrganisationUpdateView(OrganisationBaseView, FormsetsUpdateView):
    form_classes = {
        'center': OrganisationCenterAdminForm,
        'region': OrganisationRegionAdminForm,
        'country': OrganisationCountryAdminForm
    }
    form_class = OrganisationCenterAdminForm
    
    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        # additionally check if the user is admin of the organisation       
        user = request.user
        if not user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied

        return super(OrganisationUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super(OrganisationUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_object(self, queryset=None):
        """
        check if the user is a center, region or country admin for the center and save 
        the result in admin_type
        """
        user = self.request.user
        obj = super(OrganisationUpdateView, self).get_object(queryset)
        if obj.country in user.get_assignable_organisation_countries():
            self.admin_type = 'country'
        elif obj.admin_region in user.get_assignable_organisation_regions():
            self.admin_type = 'region'
        else:
            self.admin_type = 'center'
        return obj

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        return self.form_classes[self.admin_type]
        
    def get_formsets(self):

        address_extra = 0
        phone_number_extra = 1

        address_count = self.object.organisationaddress_set.count()
        if address_count == 0: 
            address_extra = 1
        
        AddressInlineFormSet = inlineformset_factory(self.model, OrganisationAddress, OrganisationAddressForm, extra=address_extra, max_num=2)
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
                email_forward_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email, 
                                                                           model=EmailForward, form=AdminEmailForwardInlineForm, max_num=10)
            else:
                email_forward_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                           model=EmailForward, form=EmailForwardInlineForm, max_num=10, 
                                                                           queryset=EmailForward.objects.filter(primary=False))
            
            if self.admin_type in ['region', 'country']:    
                email_alias_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email, 
                                                                         model=EmailAlias, form=EmailAliasInlineForm, max_num=6)
            else:
                email_alias_inline_formset = None
            
            if email_forward_inline_formset:
                email_forward_inline_formset.forms += [email_forward_inline_formset.empty_form]
                formsets += [email_forward_inline_formset]
            if email_alias_inline_formset:
                email_alias_inline_formset.forms += [email_alias_inline_formset.empty_form]
                formsets += [email_alias_inline_formset]

        return formsets
    

class OrganisationSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__email__icontains', 'name_native__icontains', 'organisationaddress__city__icontains', 'organisationaddress__city_native__icontains']


class CenterTypeFilter(ViewChoicesFilter):
    name = 'center_type'
    choices = Organisation.CENTER_TYPE_CHOICES
    select_text = _('Organisation Type')
    select_all_text = _("All Organisation Types")


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Organisations')), ('2', _('Inactive Organisations')))
    select_text = _('active/inactive')
    select_all_text = _("All")
    
    def map_to_database(self, value):
        return True if (value.pk == "1") else False


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    model = Country
    filter_list = Country.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Country')
    select_all_text = _('All Countries')
    all_remove = 'center'
    remove = 'center,app_role,role_profile,p'


class AdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    model = AdminRegion
    filter_list = AdminRegion.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Region')
    select_all_text = _('All Regions')
    all_remove = 'region,center'
    remove = 'region,center,app_role,role_profile,p'
    

class MyOrganisationsFilter(ViewButtonFilter):
    name = 'my_organisations'
    select_text = _('My Organisations')
    
    def apply(self, view, qs, default=''):
        if not view.request.user.is_superuser and view.request.user.get_administrable_organisations().exists():
            value = self.get_value_from_query_param(view, default)
            if value:
                qs = view.request.user.get_administrable_organisations()
            setattr(view, self.name, value)
            return qs
        else:
            return qs
        

class Distance(object):
    verbose_name = _('distance')
    sortable = True
    
    def __str__(self):
        return 'distance'


class OrganisationList(ListView):
    template_name = 'organisations/organisation_list.html'
    model = Organisation
    list_display = ['name', _('picture'), 'email', 'google maps', 'country', 'founded']
    
    def get_list_display(self):
        latlng = self.request.GET.get('latlng', '')
        if latlng:
            list_display = self.list_display + [Distance()]
        else:
            list_display = self.list_display
        return list_display
    
    def get_default_ordering(self):
        latlng = self.request.GET.get('latlng', '')
        if latlng:
            return ['distance']
        else:
            return ['name']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationList, self).dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        self.cl = main.ChangeList(self.request, self.model, self.get_list_display(), default_ordering=self.get_default_ordering())
        qs = super(OrganisationList, self).get_queryset().only('location', 'uuid', 'name', 'email', 'country', 'founded').prefetch_related('country', 'email', 'organisationpicture_set')
        
        # apply filters
        qs = MyOrganisationsFilter().apply(self, qs) 
        qs = OrganisationSearchFilter().apply(self, qs) 
        qs = CenterTypeFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        # offer is_active filter only for admins
        if self.request.user.is_organisation_admin:  
            qs = IsActiveFilter().apply(self, qs)
        else:
            qs = qs.filter(is_active=True)

        latlng = self.request.GET.get('latlng', '')
        if latlng:
            from django.contrib.gis import geos
            (lat, lng) = tuple(latlng.split(','))
            point = geos.fromstr("POINT(%s %s)" % (lng, lat))
            qs = get_near_organisations(point, None, qs, False)            

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
        
        my_organisations_filter = MyOrganisationsFilter().get(self)
        center_type_filter = CenterTypeFilter().get(self)
        country_filter = CountryFilter().get(self)
        admin_region_filter = AdminRegionFilter().get(self)
        
        filters = [my_organisations_filter, country_filter, admin_region_filter, center_type_filter]
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
        }
        context.update(kwargs)
        return super(OrganisationList, self).get_context_data(**context)


@login_required
def organisation_list_csv(request, type):
    # Create the HttpResponse object with the appropriate CSV header.
    if type == 'csv':
        response = HttpResponse(content_type='text/csv;charset=utf-8;')
        response['Content-Disposition'] = 'attachment; filename="organisations.csv"'
    else:
        response = HttpResponse(content_type='text;charset=utf-8;')

    writer = UnicodeWriter(response, quoting=csv.QUOTE_MINIMAL)
    row = ["name", "homepage", "email", "primary_phone", "country", "addressee", "street_address", "city", "postal_code"]
    writer.writerow(row)
    for organisation in Organisation.objects.filter(is_active=True).prefetch_related('country', 'email', 'organisationphonenumber_set', 'organisationaddress_set', 'organisationaddress_set__country'):
        row = [organisation.name, organisation.homepage, str(organisation.email), str(organisation.primary_phone), str(organisation.country)]

        primary_address = organisation.primary_address
        if not organisation.is_private and primary_address:
            row += [primary_address.addressee, primary_address.street_address, primary_address.city, primary_address.postal_code]
        else:
            row += ['', '', '', '']

        writer.writerow(row)

    return response
