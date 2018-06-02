import logging

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('status', 'user_link', 'completed_by_user', 'last_modified_by_user', 'last_modified')
    raw_id_fields = ("user", "last_modified_by_user", "completed_by_user")
    search_fields = ('user__username', 'message')
    ordering = ['-last_modified']
    date_hierarchy = 'last_modified'
    readonly_fields = ['uuid']
    list_filter = ('status', 'last_modified')

    @mark_safe
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=(obj.user.pk,), current_app=self.admin_site.name)
        return '<a href="%s">%s</a>' % (url, obj.user)

    user_link.short_description = _('user')
    user_link.admin_order_field = 'user'
