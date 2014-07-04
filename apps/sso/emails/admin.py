# -*- coding: utf-8 -*-
from django.contrib import admin

import logging

logger = logging.getLogger(__name__)


class EmailAdmin(admin.ModelAdmin):
    search_fields = ('email', 'name', 'uuid')
    list_display = ('email', 'email_type', 'last_modified', 'uuid')
    list_filter = ('email_type',)


class EmailAliasAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    search_fields = ('email__email', 'alias', 'uuid')
    list_display = ('alias', 'email', 'last_modified', 'uuid')
    list_filter = ('email__email_type', 'email')


class EmailForwardAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    search_fields = ('email__email', 'forward', 'uuid')
    list_display = ('forward', 'email', 'last_modified', 'uuid')
    list_filter = ('email__email_type', 'email')
