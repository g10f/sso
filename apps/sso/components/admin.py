import logging

from django.contrib import admin
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
