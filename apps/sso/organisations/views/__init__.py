import csv
import logging
from urllib.parse import urlunsplit

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, CreateView
from l10n.models import Country
from sso.emails.forms import AdminEmailForwardInlineForm, EmailForwardInlineForm, EmailAliasInlineForm
from sso.emails.models import EmailForward, Email, EmailAlias
from sso.forms.helpers import get_optional_inline_formset
from sso.oauth2.models import allowed_hosts
from sso.organisations.forms import OrganisationAddressForm, OrganisationPhoneNumberForm, \
    OrganisationCountryAdminForm, OrganisationRegionAdminForm, OrganisationCenterAdminForm, \
    OrganisationRegionAdminCreateForm, OrganisationCountryAdminCreateForm, OrganisationPictureForm, \
    OrganisationAssociationAdminCreateForm, OrganisationAssociationAdminForm
from sso.organisations.models import AdminRegion, Organisation, OrganisationPicture, Association, multiple_associations
from sso.organisations.models import OrganisationAddress, OrganisationPhoneNumber, get_near_organisations
from sso.utils.url import get_safe_redirect_uri
from sso.views import main
from sso.views.generic import FormsetsUpdateView, ListView, SearchFilter, ViewChoicesFilter, ViewQuerysetFilter, \
    ViewButtonFilter
from sso.views.mixins import MessagesMixin

logger = logging.getLogger(__name__)


def get_last_modified(request, *args, **kwargs):
    center_last_modified = Organisation.objects.latest("last_modified").last_modified
    address_last_modified = OrganisationAddress.objects.latest("last_modified").last_modified
    phonenumber_last_modified = OrganisationPhoneNumber.objects.latest("last_modified").last_modified
    last_modified = max(center_last_modified, address_last_modified, phonenumber_last_modified)
    return last_modified


class OrganisationBaseView(MessagesMixin):
    model = Organisation
    slug_field = slug_url_kwarg = 'uuid'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Insert the redirect_uri into the context dict.
        """
        context = {'multiple_associations': multiple_associations()}
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        if redirect_uri:
            context['redirect_uri'] = redirect_uri

        if self.object and self.request.user.is_authenticated:
            context['has_organisation_access'] = self.request.user.has_organisation_access(self.object.uuid)

        context.update(kwargs)
        return super().get_context_data(**context)

    def get_success_url(self):
        if "_continue" in self.request.POST:
            success_url = urlunsplit(('', '', self.request.path, self.request.GET.urlencode(safe='/'), ''))
            self.update_and_continue_message()
        else:
            redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
            if redirect_uri:
                success_url = redirect_uri
            else:
                # hack?
                success_url = super(FormsetsUpdateView, self).get_success_url()
                self.create_message()

        return success_url


class OrganisationDetailView(OrganisationBaseView, DetailView):
    pass


class OrganisationDeleteView(OrganisationBaseView, DeleteView):
    def get_success_url(self):
        return reverse('organisations:organisation_list')

    @method_decorator(permission_required('organisations.delete_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the organisation
        if not request.user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

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
    form_classes = {
        'email_management': {
            'region': OrganisationRegionAdminCreateForm,
            'country': OrganisationCountryAdminCreateForm,
            'association': OrganisationAssociationAdminCreateForm
        },
        'default': {
            'region': OrganisationRegionAdminForm,
            'country': OrganisationCountryAdminForm,
            'association': OrganisationAssociationAdminForm
        }
    }
    template_name_suffix = '_create_form'

    def get_success_url(self):
        return urlunsplit(('', '', reverse('organisations:organisation_update', args=[self.object.uuid.hex]),
                           self.request.GET.urlencode(safe='/'), ''))

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.add_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_form_class(self):
        """
        Returns the form class to use in this view.
        """
        user = self.request.user

        email_management = 'email_management' if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT else 'default'

        if user.get_assignable_associations().exists():
            admin_type = 'association'
        elif user.get_assignable_organisation_countries().exists():
            admin_type = 'country'
        elif user.get_assignable_organisation_regions().exists():
            admin_type = 'region'
        else:
            raise PermissionDenied

        return self.form_classes[email_management][admin_type]


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

        return super().dispatch(request, *args, **kwargs)

    def get_formsets(self):

        picture_number_extra = 1
        PictureInlineFormSet = inlineformset_factory(self.model, OrganisationPicture, OrganisationPictureForm, extra=picture_number_extra, max_num=3)

        if self.request.method == 'POST':
            picture_inline_formset = PictureInlineFormSet(self.request.POST, files=self.request.FILES, instance=self.object)
        else:
            picture_inline_formset = PictureInlineFormSet(instance=self.object)

        return [picture_inline_formset]


class OrganisationUpdateView(OrganisationBaseView, FormsetsUpdateView):
    form_classes = {
        'center': OrganisationCenterAdminForm,
        'region': OrganisationRegionAdminForm,
        'country': OrganisationCountryAdminForm,
        'association': OrganisationAssociationAdminForm
    }
    form_class = OrganisationCenterAdminForm

    @method_decorator(login_required)
    @method_decorator(permission_required('organisations.change_organisation', raise_exception=True))
    def dispatch(self, request, *args, **kwargs):
        # additionally check if the user is admin of the organisation
        user = request.user
        if not user.has_organisation_access(kwargs.get('uuid')):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self, queryset=None):
        """
        check if the user is a center, region or country admin for the center and save
        the result in admin_type
        """
        obj = super().get_object(queryset)
        self.set_admin_type(obj)
        return obj

    def set_admin_type(self, obj):
        user = self.request.user
        if obj.association in user.get_assignable_associations():
            self.admin_type = 'association'
        elif obj.organisation_country in user.get_assignable_organisation_countries():
            self.admin_type = 'country'
        elif obj.admin_region in user.get_assignable_organisation_regions():
            self.admin_type = 'region'
        else:
            self.admin_type = 'center'

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

        formsets = [address_inline_formset, phone_number_inline_formset]

        if settings.SSO_ORGANISATION_EMAIL_MANAGEMENT:
            if self.request.user.has_perm('organisations.add_organisation'):
                email_forward_inline_formset = get_optional_inline_formset(
                    self.request, self.object.email, Email, model=EmailForward, form=AdminEmailForwardInlineForm, max_num=10)
            else:
                email_forward_inline_formset = get_optional_inline_formset(
                    self.request, self.object.email, Email, model=EmailForward, form=EmailForwardInlineForm, max_num=10,
                    queryset=EmailForward.objects.filter(primary=False))

            if self.admin_type in ['region', 'country', 'association']:
                email_alias_inline_formset = get_optional_inline_formset(self.request, self.object.email, Email,
                                                                         model=EmailAlias, form=EmailAliasInlineForm,
                                                                         max_num=6)
            else:
                email_alias_inline_formset = None

            if email_forward_inline_formset:
                formsets += [email_forward_inline_formset]
            if email_alias_inline_formset:
                formsets += [email_alias_inline_formset]

        return formsets


class MyOrganisationDetailView(OrganisationBaseView, DetailView):
    """
    View of the center the user belongs to.
    """
    template_name = "organisations/my_organisation_detail.html"

    def get_object(self, queryset=None):
        return self.request.user.organisations.first()


class OrganisationSearchFilter(SearchFilter):
    search_names = ['name__icontains', 'email__email__icontains', 'name_native__icontains',
                    'organisationaddress__city__icontains', 'organisationaddress__city_native__icontains']


class CenterTypeFilter(ViewChoicesFilter):
    name = 'center_type'
    choices = settings.CENTER_TYPE_CHOICES
    select_text = _('Organisation Type')
    select_all_text = _("All Organisation Types")


class CoordinatesTypeFilter(ViewChoicesFilter):
    name = 'coordinates_type'
    choices = Organisation.COORDINATES_TYPE_CHOICES + (('0', _('None')),)
    select_text = _('Coordinates Type')
    select_all_text = _("All Coordinates Types")

    def map_to_database(self, qs_name, value):
        if value.pk == '0':
            return {qs_name: ''}
        return {qs_name: value.pk}


class IsActiveFilter(ViewChoicesFilter):
    name = 'is_active'
    choices = (('1', _('Active Organisations')), ('2', _('Inactive Organisations')))
    select_text = _('active/inactive')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class IsLiveFilter(ViewChoicesFilter):
    name = 'is_live'
    choices = (('1', _('Live Organisations')), ('2', _('Prelive Organisations')))
    select_text = _('live/prelive')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class IsPrivateFilter(ViewChoicesFilter):
    name = 'is_private'
    choices = (('1', _('Private Organisations')), ('2', _('Public Organisations')))
    select_text = _('private/public')
    select_all_text = _("All")

    def map_to_database(self, qs_name, value):
        return {qs_name: True if (value.pk == "1") else False}


class AssociationFilter(ViewQuerysetFilter):
    name = 'association'
    qs_name = 'association'
    model = Association
    select_text = _('Association')
    select_all_text = _('All Associations')
    # remove = 'country,p'
    # all_remove = 'country'


class CountryFilter(ViewQuerysetFilter):
    name = 'country'
    qs_name = 'organisationaddress__country'
    model = Country
    filter_list = Country.objects.filter(organisationaddress__isnull=False)
    select_text = _('Country')
    select_all_text = _('All Countries')
    all_remove = 'admin_region'
    remove = 'admin_region,p'


class AdminRegionFilter(ViewQuerysetFilter):
    name = 'admin_region'
    model = AdminRegion
    filter_list = AdminRegion.objects.filter(organisation__isnull=False).distinct()
    select_text = _('Region')
    select_all_text = _('All Regions')
    all_remove = ''
    remove = 'p'


class MyOrganisationsFilter(ViewButtonFilter):
    name = 'my_organisations'
    select_text = _('My Organisations')

    def apply(self, view, qs, default=''):
        if not view.request.user.is_superuser and view.request.user.administrable_organisations_exists():
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
    list_display = ['name', _('picture'), 'email', 'coordinates_type', 'organisation_country', 'founded', 'is_active',
                    'is_live']
    if settings.SSO_REGION_MANAGEMENT:
        list_display.insert(5, 'admin_region')

    filename = None
    export = False

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
            return ['order', 'name']

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an iterable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        qs = super().get_queryset().prefetch_related('email', 'organisationpicture_set', 'organisation_country__country', 'admin_region')
        return self.apply_filters(qs)

    def get_context_data(self, **kwargs):
        headers = list(self.cl.result_headers())
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1

        my_organisations_filter = MyOrganisationsFilter().get(self)

        if multiple_associations():
            if self.country:
                associations = Association.objects.filter(
                    organisation__organisationaddress__country=self.country).distinct()
            else:
                associations = Association.objects.all()
            association_filter = AssociationFilter().get(self, associations)

            if self.association:
                countries = Country.objects.filter(
                    organisationaddress__organisation__association=self.association).distinct()
            else:
                countries = Country.objects.filter(organisationaddress__isnull=False).distinct()
        else:
            association_filter = None
            countries = Country.objects.filter(organisationaddress__isnull=False).distinct()

        country_filter = CountryFilter().get(self, countries)
        center_type_filter = CenterTypeFilter().get(self)
        coordinates_type_filter = CoordinatesTypeFilter().get(self)
        if self.country:
            admin_regions = AdminRegion.objects.filter(organisation_country__country=self.country)
        else:
            admin_regions = AdminRegion.objects.none()
        admin_region_filter = AdminRegionFilter().get(self, admin_regions)

        filters = [my_organisations_filter, association_filter, country_filter, admin_region_filter,
                   center_type_filter, IsPrivateFilter().get(self), coordinates_type_filter]
        # is_active filter is only for admins
        if self.request.user.is_organisation_admin:
            filters.append(IsActiveFilter().get(self))
            filters.append(IsLiveFilter().get(self))

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
        return super().get_context_data(**context)

    def get(self, request, *args, **kwargs):
        if self.export:
            return self.get_export()
        else:
            return super().get(self, request, *args, **kwargs)

    def apply_filters(self, qs):
        # create the change list, which is required for apply filter
        self.cl = main.ChangeList(self.request, self.model, self.get_list_display(),
                                  default_ordering=self.get_default_ordering())

        qs = MyOrganisationsFilter().apply(self, qs)
        qs = OrganisationSearchFilter().apply(self, qs)
        qs = CenterTypeFilter().apply(self, qs)
        qs = CoordinatesTypeFilter().apply(self, qs)
        qs = AssociationFilter().apply(self, qs)
        qs = CountryFilter().apply(self, qs)
        qs = AdminRegionFilter().apply(self, qs)
        qs = IsPrivateFilter().apply(self, qs)
        # offer is_active and is_live filter only for admins
        if self.request.user.is_organisation_admin:
            qs = IsActiveFilter().apply(self, qs)
            qs = IsLiveFilter().apply(self, qs)
        else:
            qs = qs.filter(is_active=True)
            qs = qs.filter(is_live=True)

        latlng = self.request.GET.get('latlng', '')
        if latlng:
            from django.contrib.gis import geos
            (lat, lng) = tuple(latlng.split(','))
            point = geos.fromstr("POINT(%s %s)" % (lng, lat), srid=4326)
            qs = get_near_organisations(point, None, qs, False)

        # Set ordering.
        ordering = self.cl.get_ordering(self.request, qs)
        qs = qs.order_by(*ordering)
        return qs.distinct()

    def get_export(self):
        qs = Organisation.objects.prefetch_related('organisation_country__country', 'admin_region', 'email',
                                                   'organisationphonenumber_set',
                                                   'organisationaddress_set', 'organisationaddress_set__country')
        qs = self.apply_filters(qs)

        response = HttpResponse(content_type=self.content_type)
        if self.filename:
            response['Content-Disposition'] = 'attachment; filename="%s"' % self.filename

        writer = csv.writer(response, quoting=csv.QUOTE_ALL)
        row = ["name", "is_active", "homepage", "email", "primary_phone", "country", "admin_region", "addressee",
               "careof", "street_address", "city", "postal_code", "founded"]
        writer.writerow(row)
        for organisation in qs:
            admin_region = str(organisation.admin_region) if organisation.admin_region else str('')
            primary_phone = str(organisation.primary_phone) if organisation.primary_phone else str('')
            row = [organisation.name, str(organisation.is_active), organisation.homepage,
                   str(organisation.email), primary_phone,
                   str(organisation.organisation_country), admin_region]

            primary_address = organisation.primary_address
            if not organisation.is_private and primary_address:
                row += [primary_address.addressee, primary_address.careof, primary_address.street_address,
                        primary_address.city, primary_address.postal_code]
            else:
                row += ['', '', '', '', '']

            row += [organisation.founded]

            writer.writerow(row)

        return response
