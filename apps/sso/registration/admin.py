from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext
from .models import RegistrationProfile, RegistrationManager, send_set_password_email, send_validation_email


class ExpiredFilter(SimpleListFilter):
    parameter_name = 'expired'
    title = _('expired')

    def lookups(self, request, model_admin):
        return [('1', _('Yes')), ('0', _('No'))]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(RegistrationManager.expired_q())
        elif self.value() == '0':
            return queryset.exclude(RegistrationManager.expired_q())
        else:
            return queryset.all()


class IsActiveFilter(SimpleListFilter):
    parameter_name = 'is_active'
    title = _('active')

    def lookups(self, request, model_admin):
        return [('1', _('Yes')), ('0', _('No'))]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(user__is_active=True)
        elif self.value() == '0':
            return queryset.filter(user__is_active=False)
        else:
            return queryset.all()


class RegistrationAdmin(admin.ModelAdmin):
    actions = ['activate', 'validate_users', 'resend_validation_email', 'delete_expired']
    list_display = ('user', 'primary_email', 'date_registered', 'about_me', 'is_validated', 'token_valid',
                    'activation_valid', 'is_access_denied', 'is_active')
    raw_id_fields = ['user', 'verified_by_user', 'last_modified_by_user']
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__useremail__email')
    date_hierarchy = 'date_registered'
    list_filter = ['is_validated', ExpiredFilter, IsActiveFilter, 'check_back']
    list_select_related = True
    readonly_fields = ['last_modified', 'is_active', 'user_link']
    fieldsets = [
        (None,
         {'fields':
              ['user', 'user_link', 'last_modified', 'last_modified_by_user', 'date_registered', 'is_validated',
               'is_active', 'about_me','known_person1_first_name', 'known_person2_first_name',
               'known_person1_last_name', 'known_person2_last_name', 'check_back', 'is_access_denied',
               'verified_by_user', 'comment'],
          'classes': ['wide']}), ]

    def get_queryset(self, request):
        return super(RegistrationAdmin, self).get_queryset(request).prefetch_related('user__useremail_set')

    def is_active(self, obj):
        return obj.user.is_active

    is_active.boolean = True
    is_active.short_description = _('active')

    def primary_email(self, obj):
        return obj.user.primary_email()

    @mark_safe
    def user_link(self, obj):
        user = obj.user
        url = reverse('admin:%s_%s_change' % (user._meta.app_label, user._meta.module_name), args=[user.pk],
                      current_app=self.admin_site.name)
        return u'<a href="%s">%s</a>' % (url, user)

    user_link.short_description = _('user')

    def user_message(self, request, changecount, action_result_text=_('changed successfully')):
        if changecount:
            opts = self.model._meta
            if changecount == 1:
                name = force_text(opts.verbose_name)
            else:
                name = force_text(opts.verbose_name_plural)

            msg = ungettext("%(count)s %(name)s was %(action_result_text)s.",
                            "%(count)s %(name)s were %(action_result_text)s.",
                            changecount) % {'count': changecount,
                                            'name': name,
                                            'action_result_text': action_result_text}
            self.message_user(request, msg)

    def activate(self, request, queryset):
        users = get_user_model().objects.filter(is_active=False, registrationprofile__in=queryset)
        changecount = 0
        for user in users:
            user.is_active = True
            user.save()
            changecount += 1
            send_set_password_email(user, request)

        self.user_message(request, changecount, _('activated'))

    activate.short_description = _('Activate users')

    def delete_expired(self, request, queryset):
        expired_profiles = queryset.filter(
            id__in=RegistrationProfile.objects.get_expired().values_list('id', flat=True))
        changecount = expired_profiles.count()
        for profile in expired_profiles:
            profile.user.delete()
        self.user_message(request, changecount, _('deleted'))

    delete_expired.short_description = _('Delete inactive, expired and not validated users')

    def validate_users(self, request, queryset):
        """
        validates the selected users, if they are not alrady
        validated.        
        """
        queryset = queryset.filter(is_validated=False)
        changecount = 0
        for profile in queryset:
            profile.is_validated = True
            profile.save()
            changecount += 1
        self.user_message(request, changecount)

    validate_users.short_description = _("Mark profiles as validated")

    def resend_validation_email(self, request, queryset):
        queryset = queryset.filter(is_validated=False)
        changecount = 0
        for profile in queryset:
            send_validation_email(profile, request)
            changecount += 1
        self.user_message(request, changecount, _('an email sent'))

    resend_validation_email.short_description = _("Re-send validation emails")

    def save_model(self, request, obj, form, change):
        obj.save()
        if "_activate" in request.POST:
            self.activate(request, [obj])

# admin.site.register(RegistrationProfile, RegistrationAdmin)
