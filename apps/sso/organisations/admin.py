# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from django.conf.urls import *  # @UnusedWildImport
from l10n.models import Country
from .models import OrganisationAddress, OrganisationPhoneNumber


class CountryListFilter(SimpleListFilter):
    title = _('Country')
    parameter_name = 'country_id'
    filter_kwargs = {'organisation__isnull': False}

    def lookups(self, request, model_admin):
        qs = Country.objects.filter(**self.filter_kwargs).distinct()
        rg = [('-', _('(None)'))]
        for entry in qs:
            rg.append((str(entry.id), entry.printable_name))
        return rg

    def queryset(self, request, queryset):
        if self.value() == '-':
            return queryset.filter(country__isnull=True).distinct()
        elif self.value():
            return queryset.filter(country__id=self.value()).distinct()
        else:
            return queryset.all()


class OrganisationCountryListFilter(CountryListFilter):
    filter_kwargs = {'organisation__isnull': False}


class AdminRegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'last_modified')
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'uuid')


class Address_Inline(admin.StackedInline):
    model = OrganisationAddress
    extra = 0
    max_num = 2
    fieldsets = [
        (None,
         {'fields':
          ['address_type', 'addressee', 'street_address', 'careof', 'postal_code', 'city',
           'country', 'state', 'primary', ],
          'classes': ['wide'], }),
    ]


class AddressAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'city', 'address_type', 'addressee', 'addressee_add', 'careof')

class PhoneNumber_Inline(admin.TabularInline):
    model = OrganisationPhoneNumber
    extra = 1
    max_num = 6
    fieldsets = [
        (None,
         {'fields':
          ['phone_type', 'phone', 'primary'],
          'classes': ['wide'], }),
    ]


class OrganisationAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("css/adminstyle.css",)
        }

    ordering = ['name']
    save_on_top = True
    search_fields = ('email', 'name', 'homepage', 'uuid')
    inlines = [PhoneNumber_Inline, Address_Inline]
    readonly_fields = ['uuid', 'last_modified', 'google_maps_link']
    date_hierarchy = 'founded'
    list_filter = ('is_active', 'is_private', 'admin_region', OrganisationCountryListFilter, 'center_type',
                   'organisationaddress__address_type', 'organisationphonenumber__phone_type')
    list_display = ('id', 'name', 'email', 'last_modified', 'homepage_link', 'google_maps_link', )
    fieldsets = [
        (None,
         {'fields':
          ['uuid', 'centerid', 'name', 'center_type', 'country', 'admin_region', 'founded', ('latitude', 'longitude', 'google_maps_link'),
           'email', 'homepage', 'is_active', 'is_private', 'last_modified'], 
          'classes': ['wide', 'wide_ex']}),
        (_('notes'),
         {'fields':
          ['notes'],
          'classes': ['collapse', 'wide'], }),
    ]

    def save_model(self, request, obj, form, change):
        if form.has_changed():
            return super(OrganisationAdmin, self).save_model(request, obj, form, change)
