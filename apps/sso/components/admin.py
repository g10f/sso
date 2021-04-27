import logging

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from sso.oauth2.keys import clear_cache
from .models import ComponentConfig

logger = logging.getLogger(__name__)


class ComponentConfigInline(admin.StackedInline):
    model = ComponentConfig
    fk_name = 'component'
    extra = 1
    fieldsets = ((None, {'fields': (('name', 'value'),), 'classes': ['wide']}),)


class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'created_at')
    search_fields = ('name', 'uuid')
    date_hierarchy = 'last_modified'
    list_filter = ('created_at', 'componentconfig__name')
    inlines = [ComponentConfigInline]

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('clear_signing_keys_cache/', self.admin_site.admin_view(self.clear_signing_keys_cache), name='clear_signing_keys_cache'),
        ]
        return my_urls + urls

    def clear_signing_keys_cache(self, request):
        clear_cache()
        return HttpResponse()
