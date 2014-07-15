# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from l10n.models import CONTINENTS
from sso.views import main
from sso.emails.models import EmailForward, EmailAlias
from sso.organisations.models import OrganisationCountry, CountryGroup
from sso.views.generic import FormsetsUpdateView, ListView, ViewChoicesFilter, SearchFilter, ViewQuerysetFilter
from sso.emails.forms import AdminEmailForwardForm, EmailAliasForm
from sso.organisations.forms import OrganisationCountryForm
from sso.organisations.views import get_optional_email_inline_formset

import logging
logger = logging.getLogger(__name__)


class OrganisationCountryBaseView(object):
    model = OrganisationCountry
    slug_field = slug_url_kwarg = 'uuid'
    
    def get_context_data(self, **kwargs):
        context = {}
        if self.object and self.request.user.is_authenticated():
            context['has_country_access'] = self.request.user.has_country_access(self.object.uuid)
        
        context.update(kwargs)
        return super(OrganisationCountryBaseView, self).get_context_data(**context)


class OrganisationCountryDetailView(OrganisationCountryBaseView, DetailView):
    pass


class OrganisationCountryUpdateView(OrganisationCountryBaseView, FormsetsUpdateView):
    form_class = OrganisationCountryForm
    
    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisationcountry', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        # additionally check if the user is admin of the country       
        if not request.user.has_country_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(OrganisationCountryUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_formsets(self):
        email_forward_inline_formset = get_optional_email_inline_formset(self.request, self.object.email, 
                                                                         Model=EmailForward, Form=AdminEmailForwardForm, max_num=10)
        email_alias_inline_formset = get_optional_email_inline_formset(self.request, self.object.email, 
                                                                       Model=EmailAlias, Form=EmailAliasForm, max_num=6)
        
        formsets = []
        if email_forward_inline_formset:
            email_forward_inline_formset.forms += [email_forward_inline_formset.empty_form]
            formsets += [email_forward_inline_formset]
        if email_alias_inline_formset:
            email_alias_inline_formset.forms += [email_alias_inline_formset.empty_form]
            formsets += [email_alias_inline_formset]
        
        return formsets
    

class ContinentsFilter(ViewChoicesFilter):
    name = 'continent'
    qs_name = 'country__continent'
    choices = CONTINENTS
    select_text = _('Select Continent')
    select_all_text = _("All Continents")


class CountrySearchFilter(SearchFilter):
    search_names = ['country__name__icontains', 'email__email__icontains']


class CountryGroupFilter(ViewQuerysetFilter):
    name = 'country_group'
    qs_name = 'country_groups'
    model = CountryGroup
    select_text = _('Select Group')
    select_all_text = _('All Groups')


class OrganisationCountryList(ListView):
    template_name = 'organisations/organisationcountry_list.html'
    model = OrganisationCountry
    list_display = ['country', 'email', 'homepage']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationCountryList, self).dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        qs = super(OrganisationCountryList, self).get_queryset().select_related('country', 'email')
            
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['country'])
        
        qs = CountrySearchFilter().apply(self, qs)  
        qs = ContinentsFilter().apply(self, qs)
        qs = CountryGroupFilter().apply(self, qs)
        
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
        
        continent_filter = ContinentsFilter().get(self)
        
        filters = [continent_filter]
        # offer is_active filter only for admins
        if self.request.user.is_organisation_admin:  
            filters.append(CountryGroupFilter().get(self))
        
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
        return super(OrganisationCountryList, self).get_context_data(**context)
