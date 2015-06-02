from django.contrib import admin
from sso.auth.models import Device, TwilioSMSDevice, TOTPDevice


class DeviceAdmin(admin.ModelAdmin):
    search_fields = 'user__name',
    list_filter = 'confirmed',
    list_display = 'user', 'confirmed', 'created_at', 'last_used'


class TOTPDeviceAdmin(admin.ModelAdmin):
    pass


class TwilioSMSDeviceAdmin(admin.ModelAdmin):
    pass


admin.site.register(Device, DeviceAdmin)
admin.site.register(TwilioSMSDevice, TwilioSMSDeviceAdmin)
admin.site.register(TOTPDevice, TOTPDeviceAdmin)
