# -*- coding: utf-8 -*-
import logging

from django import forms
from django.core import urlresolvers
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from sso.oauth2.models import CONFIDENTIAL_CLIENTS

logger = logging.getLogger(__name__)
   

class ClientAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(ClientAdminForm, self).clean()
        type = cleaned_data.get("type")
        client_secret = cleaned_data.get("client_secret")
        user = cleaned_data.get("user")

        if type and client_secret:
            # Only do something if both fields are valid so far.
            if type not in CONFIDENTIAL_CLIENTS and client_secret:
                self.add_error('client_secret', "Client secret must be empty for non-confidential client types")
        if type == 'service' and user is None:
            self.add_error('user', "User is required for service clients")


class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'application', 'type', 'user', 'is_active')
    list_filter = ('is_active', 'type', 'application')
    fields = ('application', 'type', 'name', 'uuid', 'client_secret', 'redirect_uris', 'scopes', 'user', 'notes', 'is_active', 'last_modified')
    readonly_fields = ('last_modified', )
    list_select_related = ('application', 'user')
    form = ClientAdminForm


class BearerTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_link', 'user_link', 'created_at')
    list_filter = ('client__application', 'client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__uuid', 'user__useremail__email')
    raw_id_fields = ("user",)
    readonly_fields = ('created_at', )
    list_select_related = ('user', 'client')

    def user_link(self, obj):
        url = urlresolvers.reverse('admin:accounts_user_change', args=(obj.user.pk,), current_app=self.admin_site.name)
        return mark_safe(u'<a href="%s">%s</a>' % (url, obj.user))
    user_link.allow_tags = True
    user_link.short_description = _('user')
    user_link.admin_order_field = 'user'

    def client_link(self, obj):
        url = urlresolvers.reverse('admin:oauth2_client_change', args=(obj.client.pk,), current_app=self.admin_site.name)
        return mark_safe(u'<a href="%s">%s</a>' % (url, obj.client))
    client_link.allow_tags = True
    client_link.short_description = _('client')
    client_link.admin_order_field = 'client'


class AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_link', 'user_link', 'code', 'created_at', 'redirect_uri', 'is_valid')
    list_filter = ('client__application', 'client', 'is_valid')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__uuid', 'user__useremail__email')
    raw_id_fields = ("user",)
    list_select_related = ('user', 'client')

    def user_link(self, obj):
        url = urlresolvers.reverse('admin:accounts_user_change', args=(obj.user.pk,), current_app=self.admin_site.name)
        return mark_safe(u'<a href="%s">%s</a>' % (url, obj.user))
    user_link.allow_tags = True
    user_link.short_description = _('user')
    user_link.admin_order_field = 'user'

    def client_link(self, obj):
        url = urlresolvers.reverse('admin:oauth2_client_change', args=(obj.client.pk,), current_app=self.admin_site.name)
        return mark_safe(u'<a href="%s">%s</a>' % (url, obj.client))
    client_link.allow_tags = True
    client_link.short_description = _('client')
    client_link.admin_order_field = 'client'


class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'bearer_token_link', 'created_at')
    list_filter = ('bearer_token__client__application', 'bearer_token__client')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__uuid', 'user__useremail__email')
    raw_id_fields = ("bearer_token",)
    readonly_fields = ('created_at', )
    list_select_related = ('bearer_token__user', 'bearer_token__client')

    def bearer_token_link(self, obj):
        url = urlresolvers.reverse('admin:oauth2_bearertoken_change', args=(obj.bearer_token.pk,), current_app=self.admin_site.name)
        return mark_safe(u'<a href="%s">%s</a>' % (url, obj.bearer_token))
    bearer_token_link.allow_tags = True
    bearer_token_link.short_description = _('bearer token')
    bearer_token_link.admin_order_field = 'bearer_token'
