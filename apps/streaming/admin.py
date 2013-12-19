# -*- coding: utf-8 -*-
from django.contrib import admin
from models import StreamingUser, Logging


class StreamingUserAdmin(admin.ModelAdmin):
    #date_hierarchy = 'created'
    list_display = ('id_nr', 'email', 'password_clear', 'center', 'admin', 'ip', 'registrar', 'mailsent', 'created', 'subscriber',)
    search_fields = ('email',)
    list_filter = ('center', 'admin', 'mailsent', 'created', 'subscriber', 'logging__date')
    readonly_fields = ('id_nr', 'email', 'password', 'password_clear', 'center', 'admin', 'ip', 'registrar', 'mailsent', 'created', 'subscriber',)
    actions = None
    
    def has_delete_permission(self, request, obj=None):
        return False

    def password_clear(self, obj):
        return obj.password.decode("base64")
    
    def queryset(self, request):
        return super(StreamingUserAdmin, self).queryset(request).select_related('registrar')


class LoggingAdmin(admin.ModelAdmin):
    #date_hierarchy = 'date'
    list_display = ('id', 'user', 'action', 'date', 'ip',)
    search_fields = ('user__email',)
    list_filter = ('date', 'action')
    readonly_fields = ('id', 'user', 'action', 'date', 'ip',)
    actions = None
    
    def has_delete_permission(self, request, obj=None):
        return False

    def queryset(self, request):
        return super(LoggingAdmin, self).queryset(request).select_related('user')
    
    
admin.site.register(StreamingUser, StreamingUserAdmin)
admin.site.register(Logging, LoggingAdmin)
