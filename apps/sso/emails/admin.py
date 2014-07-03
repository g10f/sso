# -*- coding: utf-8 -*-
from django.contrib import admin

import logging

logger = logging.getLogger(__name__)


class EmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'last_modified', 'uuid')


class EmailAliasAdmin(admin.ModelAdmin):
    list_display = ('email', 'email_list', 'last_modified', 'uuid')
    list_filter = ('email_list', )


class EmailForwardAdmin(admin.ModelAdmin):
    list_display = ('email', 'email_list', 'last_modified', 'uuid')
    list_filter = ('email_list', )
