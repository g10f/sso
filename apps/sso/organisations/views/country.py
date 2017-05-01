# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, CreateView
from l10n.models import CONTINENTS, Country
from sso.emails.forms import EmailForwardOnlyInlineForm, EmailAliasInlineForm
from sso.emails.models import EmailForward, EmailAlias, Email
from sso.forms.helpers import get_optional_inline_formset
from sso.organisations.forms import OrganisationCountryForm
from sso.organisations.models import OrganisationCountry, CountryGroup, Association, multiple_associations
from sso.views import main
from sso.views.generic import FormsetsUpdateView, ListView, ViewChoicesFilter, SearchFilter, ViewQuerysetFilter, ViewButtonFilter

logger = logging.getLogger(__name__)


class OrganisationCountryBaseView(object):
    model = OrganisationCountry
    slug_field = slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = {}
        if self.object and self.request.user.is_authenticated:
            context['has_country_access'] = self.request.user.has_country_access(self.object.uuid)

        context.update(kwargs)
        return super(OrganisationCountryBaseView, self).get_context_data(**context)


class OrganisationCountryDetailView(OrganisationCountryBaseView, DetailView):
    pass


class OrganisationCountryCreateView(OrganisationCountryBaseView, CreateView):
    template_name_suffix = '_create_form'
    form_class = OrganisationCountryForm

    def get_success_url(self):
        return reverse('organisations:organisationcountry_update', args=[self.object.uuid.hex])

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.add_organisationcountry', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(OrganisationCountryCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the associations
        """
        kwargs = super(OrganisationCountryCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


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
        formsets = []
        if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT:
            email_forward_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                       model=EmailForward, form=EmailForwardOnlyInlineForm, max_num=20)
            email_alias_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                     model=EmailAlias, form=EmailAliasInlineForm, max_num=6)

            if email_forward_inline_formset:
                email_forward_inline_formset.forms += [email_forward_inline_formset.empty_form]
                formsets += [email_forward_inline_formset]
            if email_alias_inline_formset:
                email_alias_inline_formset.forms += [email_alias_inline_formset.empty_form]
                formsets += [email_alias_inline_formset]
        return formsets

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the associations
        """
        kwargs = super(OrganisationCountryUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class AssociationFilter(ViewQuerysetFilter):
    name = 'association'
    qs_name = 'association'
    model = Association
    select_text = _('Association')
    select_all_text = _('All Associations')
    remove = 'continent,country_group'


class ContinentsFilter(ViewChoicesFilter):
    name = 'continent'
    qs_name = 'country__continent'
    choices = CONTINENTS
    select_text = _('Continent')
    select_all_text = _("All Continents")


class CountrySearchFilter(SearchFilter):
    search_names = ['country__name__icontains', 'email__email__icontains']


class CountryGroupFilter(ViewQuerysetFilter):
    name = 'country_group'
    qs_name = 'country_groups'
    model = CountryGroup
    select_text = _('Group')
    select_all_text = _('All Groups')


class MyCountriesFilter(ViewButtonFilter):
    name = 'my_countries'
    select_text = _('My Countries')

    def apply(self, view, qs, default=''):
        if not view.request.user.is_superuser and view.request.user.get_administrable_countries().exists():
            value = self.get_value_from_query_param(view, default)
            if value:
                qs = view.request.user.get_administrable_countries()
            setattr(view, self.name, value)
            return qs
        else:
            return qs


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Countries')), ('2', _('Inactive Countries')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, value):
        return True if (value.pk == "1") else False


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
        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['country'])
        qs = super(OrganisationCountryList, self).get_queryset().select_related('country', 'email')

        # apply filters
        qs = MyCountriesFilter().apply(self, qs)
        qs = CountrySearchFilter().apply(self, qs)
        qs = AssociationFilter().apply(self, qs)
        qs = ContinentsFilter().apply(self, qs)
        qs = CountryGroupFilter().apply(self, qs)
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

        my_countries_filter = MyCountriesFilter().get(self)
        association_filter = AssociationFilter().get(self)
        if multiple_associations():
            if self.association:
                continents = Country.objects.filter(organisationcountry__association=self.association).values_list('continent', flat=True)
            else:
                continents = Country.objects.values_list('continent', flat=True)
        else:
            association_filter = None
            continents = Country.objects.values_list('continent', flat=True)

        continent_choices = filter(lambda x: x[0] in continents, ContinentsFilter.choices)
        continent_filter = ContinentsFilter().get(self, continent_choices)

        filters = [my_countries_filter, association_filter, continent_filter]
        # offer is_active and CountryGroup filter only for admins
        if self.request.user.is_organisation_admin:
            filters.append(CountryGroupFilter().get(self))
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
        return super(OrganisationCountryList, self).get_context_data(**context)
