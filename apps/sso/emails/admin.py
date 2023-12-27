import logging

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import EmailAlias, EmailForward

logger = logging.getLogger(__name__)


class EmailAlias_Inline(admin.TabularInline):
    model = EmailAlias
    extra = 1
    max_num = 10
    fieldsets = [
        (None,
         {'fields':
              ['alias', ],
          'classes': ['wide'], }),
    ]


class EmailForward_Inline(admin.TabularInline):
    model = EmailForward
    extra = 1
    max_num = 10
    fieldsets = [
        (None,
         {'fields':
              ['forward', 'primary'],
          'classes': ['wide'], }),
    ]


class EmailTypeFilter(admin.SimpleListFilter):
    title = _('Email type')
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (
            ('countrygroup', _('Country group')),
            ('country', _('Country')),
            ('region', _('Region')),
            ('organisation', _('Organisation')),
            ('group', _('Group')),
            ('none', _('None')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value() == 'countrygroup':
            return queryset.filter(countrygroup__isnull=False)
        if self.value() == 'country':
            return queryset.filter(organisationcountry__isnull=False)
        if self.value() == 'organisation':
            return queryset.filter(organisation__isnull=False)
        if self.value() == 'region':
            return queryset.filter(adminregion__isnull=False)
        if self.value() == 'group':
            return queryset.filter(groupemail__isnull=False)
        if self.value() == 'none':
            return queryset.filter(countrygroup__isnull=True, organisationcountry__isnull=True,
                                   organisation__isnull=True,
                                   adminregion__isnull=True, groupemail__isnull=True)


class EmailAdmin(admin.ModelAdmin):
    show_facets = admin.ShowFacets.NEVER
    search_fields = ('email', 'uuid')
    list_display = ('email', 'email_type', 'last_modified', 'uuid')
    list_filter = (EmailTypeFilter, 'email_type', 'permission')
    inlines = [EmailAlias_Inline, EmailForward_Inline]


class EmailAliasAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    search_fields = ('email__email', 'alias', 'uuid')
    list_display = ('alias', 'email', 'last_modified', 'uuid')
    list_filter = ('email__email_type', )


class EmailForwardAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    search_fields = ('email__email', 'forward', 'uuid')
    list_display = ('forward', 'email', 'last_modified', 'uuid')
    list_filter = ('email__email_type', )


class GroupEmailAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    list_display = ('name', 'email', 'homepage', 'uuid')
    list_filter = ('email__permission', )


class GroupEmailManagerAdmin(admin.ModelAdmin):
    list_select_related = ('group_email',)
    list_display = ('group_email', 'manager')
    raw_id_fields = ('manager',)
