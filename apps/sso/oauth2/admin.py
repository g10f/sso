# -*- coding: utf-8 -*-
from django.contrib import admin
from models import AuthorizationCode, BearerToken, RefreshToken, Client

import logging
logger = logging.getLogger(__name__)
   

class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'application', 'type')
    list_filter = ('type', 'application',)
    raw_id_fields = ("user",)
    fields = ('application', 'type', 'name', 'uuid', 'client_secret', 'redirect_uris', 'scopes', 'user', 'last_modified')
    readonly_fields = ('last_modified', )
    list_select_related = ('application', )

class BearerTokenAdmin(admin.ModelAdmin):
    list_display = ('client', 'user', 'created_at')
    list_filter = ('client__application', 'client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'user__uuid')
    raw_id_fields = ("user",)
    readonly_fields = ('created_at', )


class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('bearer_token', 'created_at')
    list_filter = ('bearer_token__client__application', 'bearer_token__client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'user__uuid')
    raw_id_fields = ("bearer_token",)
    readonly_fields = ('created_at', )


class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ('client', 'user', 'code', 'created_at', 'redirect_uri', 'is_valid')
    list_filter = ('client__application', 'client', 'is_valid')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'user__uuid')
    raw_id_fields = ("user",)


admin.site.register(AuthorizationCode, AuthorizationCodeAdmin)
admin.site.register(BearerToken, BearerTokenAdmin)
admin.site.register(RefreshToken, RefreshTokenAdmin)
admin.site.register(Client, ClientAdmin)
