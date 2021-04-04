from django.contrib import admin


class ProfileAdmin(admin.ModelAdmin):
    search_fields = 'user__username',
    list_filter = 'is_otp_enabled',
    list_display = 'user', 'is_otp_enabled', 'default_device'
    raw_id_fields = ("user",)


class DeviceAdmin(admin.ModelAdmin):
    search_fields = 'user__username',
    list_filter = 'confirmed',
    list_display = 'user', 'confirmed', 'created_at', 'last_used'
    raw_id_fields = ("user",)


class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display = 'user', 'confirmed', 'created_at', 'last_used'
    raw_id_fields = ("user",)


class U2FDeviceAdmin(admin.ModelAdmin):
    list_display = 'user', 'confirmed', 'created_at', 'last_used'
    raw_id_fields = ("user",)
