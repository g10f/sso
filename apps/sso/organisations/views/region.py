import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, CreateView
from l10n.models import Country
from sso.emails.forms import EmailForwardOnlyInlineForm, EmailAliasInlineForm
from sso.emails.models import EmailForward, EmailAlias, Email
from sso.forms.helpers import get_optional_inline_formset
from sso.organisations.forms import AdminRegionForm
from sso.organisations.models import AdminRegion, Association, multiple_associations
from sso.views import main
from sso.views.generic import FormsetsUpdateView, ListView, SearchFilter, ViewQuerysetFilter, ViewButtonFilter, ViewChoicesFilter
logger = logging.getLogger(__name__)


class AdminRegionBaseView(object):
    model = AdminRegion
    slug_field = slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = {}
        if self.object and self.request.user.is_authenticated:
            context['has_region_access'] = self.request.user.has_region_access(self.object.uuid)

        context.update(kwargs)
        return super(AdminRegionBaseView, self).get_context_data(**context)


class AdminRegionDetailView(AdminRegionBaseView, DetailView):
    pass


class AdminRegionCreateView(AdminRegionBaseView, CreateView):
    template_name_suffix = '_create_form'
    form_class = AdminRegionForm

    def get_success_url(self):
        return reverse('organisations:adminregion_update', args=[self.object.uuid.hex])

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.add_adminregion', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super(AdminRegionCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super(AdminRegionCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class AdminRegionUpdateView(AdminRegionBaseView, FormsetsUpdateView):
    form_class = AdminRegionForm

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_adminregion', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the region
        if not request.user.has_region_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super(AdminRegionUpdateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super(AdminRegionUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        """
        check if the user is a center, region or country admin for the center and save
        the result in admin_type
        """
        user = self.request.user
        obj = super(AdminRegionUpdateView, self).get_object(queryset)
        if obj.organisation_country in user.get_assignable_organisation_countries():
            self.admin_type = 'country'
        else:
            self.admin_type = 'region'
        return obj

    def get_formsets(self):
        formsets = []
        if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT:
            email_forward_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                       model=EmailForward, form=EmailForwardOnlyInlineForm, max_num=10)
            if self.admin_type in ['country']:
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


class AdminRegionSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__email__icontains']


class AssociationFilter(ViewQuerysetFilter):
    name = 'association'
    qs_name = 'organisation_country__association'
    model = Association
    select_text = _('Association')
    select_all_text = _('All Associations')
    remove = 'country'


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'organisation_country__country'
    model = Country
    filter_list = Country.objects.all()
    select_text = _('Country')
    select_all_text = _('All Countries')


class MyRegionsFilter(ViewButtonFilter):
    name = 'my_regions'
    select_text = _('My Regions')

    def apply(self, view, qs, default=''):
        if not view.request.user.is_superuser and view.request.user.get_administrable_regions().exists():
            value = self.get_value_from_query_param(view, default)
            if value:
                qs = qs.filter(pk__in=view.request.user.get_administrable_regions())
            setattr(view, self.name, value)
            return qs
        else:
            return qs


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Regions')), ('2', _('Inactive Regions')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class AdminRegionList(ListView):
    template_name = 'organisations/adminregion_list.html'
    model = AdminRegion
    list_display = ['name', 'email', 'homepage', 'country']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(AdminRegionList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        qs = super(AdminRegionList, self).get_queryset().select_related('organisation_country__country', 'email')

        self.cl = main.ChangeList(self.request, self.model, self.list_display, default_ordering=['name'])

        # apply filters
        qs = MyRegionsFilter().apply(self, qs)
        qs = AdminRegionSearchFilter().apply(self, qs)
        qs = AssociationFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
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

        my_regions_filter = MyRegionsFilter().get(self)
        if multiple_associations():
            association_filter = AssociationFilter().get(self)
            if self.association:
                countries = Country.objects.filter(organisationcountry__adminregion__isnull=False, association=self.association).distinct()
            else:
                countries = Country.objects.none()
        else:
            association_filter = None
            countries = Country.objects.filter(organisationcountry__adminregion__isnull=False).distinct()

        country_filter = CountryFilter().get(self, countries)

        filters = [association_filter, my_regions_filter, country_filter]
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
        return super(AdminRegionList, self).get_context_data(**context)
