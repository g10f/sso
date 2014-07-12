# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from l10n.models import CONTINENTS
from sso.views import main
from sso.emails.models import EmailForward, EmailAlias
from sso.organisations.models import OrganisationCountry
from sso.views.generic import FormsetsUpdateView, ListView
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
            context['is_country_admin'] = self.request.user.is_country_admin(self.object.uuid)
        
        context.update(kwargs)
        return super(OrganisationCountryBaseView, self).get_context_data(**context)


class OrganisationCountryDetailView(OrganisationCountryBaseView, DetailView):
    pass


class OrganisationCountryUpdateView(OrganisationCountryBaseView, FormsetsUpdateView):
    form_class = OrganisationCountryForm
    
    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisationcountry', raise_exception=True))
    def dispatch(self, request, *args, **kwargs): 
        # additionally check if the user is admin of the organisation       
        if not request.user.is_organisation_admin(kwargs.get('uuid')):  # TODO: ...
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
        # apply search filter
        search_var = self.request.GET.get(main.SEARCH_VAR, '')
        if search_var:
            search_list = search_var.split()
            q = Q()
            for search in search_list:
                q |= Q(country__name__icontains=search) | Q(email__email__icontains=search)
            qs = qs.filter(q)
        
        # apply continent filter
        continent = self.request.GET.get('continent', '')
        if continent:
            self.continent = main.FilterItem((continent, dict(CONTINENTS)[continent]))
            qs = qs.filter(country__continent=continent)
        else:
            self.continent = None
            
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
        
        continents = [main.FilterItem(item) for item in CONTINENTS]
        filters = [{
            'selected': self.continent, 'list': continents, 'select_text': _('Select Continent'), 'select_all_text': _("All Continents"), 
            'param_name': 'continent', 'all_remove': '', 'remove': 'p'
        }]
        
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
