from django.contrib import admin


class DeviceAdmin(admin.ModelAdmin):
    search_fields = 'user__name',
    list_filter = 'confirmed',
    list_display = 'user', 'confirmed', 'created_at', 'last_used'
    raw_id_fields = ("user",)


class TOTPDeviceAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


class TwilioSMSDeviceAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


class U2FDeviceAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
