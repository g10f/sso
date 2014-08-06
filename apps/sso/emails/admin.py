# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import EmailAlias, EmailForward

import logging

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


class EmailAdmin(admin.ModelAdmin):
    search_fields = ('email', 'name', 'uuid')
    list_display = ('email', 'email_type', 'last_modified', 'uuid')
    list_filter = ('email_type', 'permission')
    inlines = [EmailAlias_Inline, EmailForward_Inline]


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


class GroupEmailAdmin(admin.ModelAdmin):
    list_select_related = ('email',)
    list_display = ('email', 'homepage', 'uuid')


class GroupEmailManagerAdmin(admin.ModelAdmin):
    list_select_related = ('group_email',)
    list_display = ('group_email', 'manager')
    raw_id_fields = ('manager',)
