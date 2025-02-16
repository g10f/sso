from reversion.admin import VersionAdmin

from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.utils import model_ngettext
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.gis.admin import GISModelAdmin
from django.utils.translation import gettext_lazy as _
from l10n.models import Country
from sso.emails.models import Email, CENTER_EMAIL_TYPE
from .models import OrganisationAddress, OrganisationPhoneNumber, OrganisationCountry, CountryGroup


class CountryListFilter(SimpleListFilter):
    title = _('Country')
    parameter_name = 'country_id'
    filter_kwargs = {'organisationcountry__isnull': False}

    def lookups(self, request, model_admin):
        qs = Country.objects.filter(**self.filter_kwargs).distinct()
        rg = [('-', _('(None)'))]
        for entry in qs:
            rg.append((str(entry.id), entry.printable_name))
        return rg

    def queryset(self, request, queryset):
        if self.value() == '-':
            return queryset.filter(organisation_country__country__isnull=True).distinct()
        elif self.value():
            return queryset.filter(organisation_country__country__id=self.value()).distinct()
        else:
            return queryset.all()


class AdminRegionAdmin(VersionAdmin, admin.ModelAdmin):
    show_facets = admin.ShowFacets.NEVER
    list_display = ('name', 'uuid', 'last_modified')
    list_filter = (CountryListFilter,)
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'uuid')


class AssociationAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ('name', 'last_modified', 'is_active', 'is_external')
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'uuid')


class CountryGroupAdminForm(forms.ModelForm):
    """
    see https://snipt.net/chrisdpratt/symmetrical-manytomany-filter-horizontal-in-django-admin/
    """
    countries = forms.ModelMultipleChoiceField(queryset=OrganisationCountry.objects.all(), required=False,
                                               widget=FilteredSelectMultiple(verbose_name=_('Countries'),
                                                                             is_stacked=False))

    class Meta:
        model = CountryGroup
        fields = ('name', 'homepage', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['countries'].initial = self.instance.countries.all()

    def save(self, commit=True):
        country_group = super().save(commit=False)

        if commit:
            country_group.save()

        if country_group.pk:
            country_group.countries = self.cleaned_data['countries']
            self.save_m2m()

        return country_group


class CountryGroupAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ('name', 'email', 'homepage', 'last_modified')
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'email', 'homepage', 'uuid')
    form = CountryGroupAdminForm


class OrganisationCountryAdmin(VersionAdmin, admin.ModelAdmin):
    list_select_related = ('country', 'email')
    list_display = ('country', 'homepage', 'email', 'is_active', 'last_modified')
    list_filter = ('association', 'country__continent', 'is_active', 'country_groups')
    filter_horizontal = ('country_groups',)
    date_hierarchy = 'last_modified'
    search_fields = ('country__name', 'uuid')


class Address_Inline(admin.StackedInline):
    model = OrganisationAddress
    extra = 0
    max_num = 2
    fieldsets = [
        (None,
         {'fields':
              ['address_type', 'addressee', 'street_address', 'careof', 'postal_code', 'city',
               'country', 'region', 'primary', ],
          'classes': ['wide'], }),
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # display only countries where there is a corresponding entry in organisationcountry table
        if db_field.name == "country":
            kwargs["queryset"] = Country.objects.filter(active=True)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'city', 'address_type', 'addressee', 'addressee_add', 'careof')


class PhoneNumber_Inline(admin.TabularInline):
    model = OrganisationPhoneNumber
    extra = 1
    max_num = 6
    fieldsets = [
        (None,
         {'fields': ['phone_type', 'phone'],
          'classes': ['wide'], }),
    ]


class OrganisationAdmin(VersionAdmin, GISModelAdmin):
    show_facets = admin.ShowFacets.NEVER
    list_select_related = ('organisation_country__country', 'email', 'association')
    actions = GISModelAdmin.actions + ('mark_uses_user_activation',)
    save_on_top = True
    search_fields = ('name', 'uuid')
    inlines = [PhoneNumber_Inline, Address_Inline]
    readonly_fields = ['last_modified', 'google_maps_link']
    non_su_readonly_fields = ['uuid', 'last_modified', 'google_maps_link']
    date_hierarchy = 'founded'
    raw_id_fields =  ['last_modified_by_user']
    list_filter = (
        'association', 'is_active', 'is_private', 'is_live', 'is_selectable', 'uses_user_activation', 'coordinates_type', 'admin_region',
        'organisation_country__country__continent', CountryListFilter, 'center_type',
        'organisationaddress__address_type', 'organisationphonenumber__phone_type')
    list_display = ('slug', 'name', 'name_native', 'email', 'last_modified', 'homepage_link', 'google_maps_link',)
    fieldsets = [
        (None,
         {'fields':
              ['uuid', 'centerid', 'order', 'name', 'name_native', 'slug', 'center_type', 'association',
               'organisation_country', 'last_modified_by_user',
               'admin_region', 'founded', ('coordinates_type', 'google_maps_link'),
               'location', 'email', 'homepage', 'source_urls', 'is_active', 'is_private', 'is_live', 'is_selectable',
               'uses_user_activation', 'neighbour_distance', 'transregional_distance',
               'last_modified'],
          'classes': ['wide']}),
        (_('notes'),
         {'fields':
              ['notes'],
          'classes': ['collapse', 'wide'], }),
    ]

    # performance optimisation for MembershipInline autocomplete_field organisation
    def get_search_results(self, request, queryset, search_term):
        queryset = queryset.select_related('organisation_country__country', 'email', 'association').distinct()
        return super().get_search_results(request, queryset, search_term)

    def mark_uses_user_activation(self, request, queryset):
        n = queryset.update(uses_user_activation=True)
        self.message_user(request, _("Successfully updated %(count)d %(items)s.") % {
            "count": n, "items": model_ngettext(self.opts, n)})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "email":
            kwargs["queryset"] = Email.objects.filter(email_type=CENTER_EMAIL_TYPE)

        if db_field.name == "organisation_country":
            kwargs["queryset"] = OrganisationCountry.objects.filter(is_active=True).select_related('country')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if form.has_changed():
            return super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return super().get_readonly_fields(request, obj)
        else:
            return self.non_su_readonly_fields
