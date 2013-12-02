# -*- coding: utf-8 -*-
from django.contrib import admin
from django.template.response import TemplateResponse
from django.core.mail.message import EmailMessage
from django.conf import settings
from django.utils.encoding import force_unicode
from django.contrib.admin.util import model_ngettext
from django.db.models import Q
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin, GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core import urlresolvers
from django.utils.safestring import mark_safe
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from sorl.thumbnail.admin import AdminImageMixin

from models import Application, Organisation, Region, ApplicationRole, Role, UserAssociatedSystem
from .forms import UserCreationForm, BasicUserChangeForm, AdminUserChangeForm
import logging

logger = logging.getLogger(__name__)

admin.site.unregister(Group)


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('order', 'link', 'url', 'enable_url', 'uuid')
    list_filter = ('enable_url', )


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')


class ApplicationRoleAdmin(admin.ModelAdmin):
    list_filter = ('application', 'role',)
    list_display = ('__unicode__', 'is_inheritable_by_org_admin', 'is_inheritable_by_global_admin')


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'uuid', 'last_modified')
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'uuid')


class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'iso2_code', 'uuid', 'last_modified')
    date_hierarchy = 'last_modified'
    search_fields = ('name', 'uuid')
    list_filter = ('region', 'iso2_code')


class BaseFilter(SimpleListFilter):
    def get_lookup_qs(self, request, model_admin):
        """ Return the queryset for the filter"""
        raise NotImplementedError
        
    def lookups(self, request, model_admin):
        qs = self.get_lookup_qs(request, model_admin)
        rg = [('-', _('(None)'))]
        for entry in qs:
            rg.append((str(entry.id), unicode(entry)))
        return rg
    
    def queryset(self, request, queryset):
        if self.value() == '-':
            kwargs = {'%s__isnull' % self.field_path: True}
            return queryset.filter(**kwargs).distinct()
        elif self.value():
            kwargs = {'%s__id' % self.field_path: self.value()}
            return queryset.filter(**kwargs).distinct()
        else:
            return queryset.all()


class OrganisationsListFilter(BaseFilter):
    """
    Fiter for user admin
    """
    title = _('Organisation')
    parameter_name = 'organisation'
    field_path = 'organisations'
    
    def get_lookup_qs(self, request, model_admin):
        return Organisation.objects.filter(user__isnull=False).distinct()


class LastModifiedUserFilter(BaseFilter):
    title = _('last modified by')
    parameter_name = 'last_modified_by_user'
    field_path = 'last_modified_by_user'
    
    def get_lookup_qs(self, request, model_admin):
        last_modified_by_user_ids = get_user_model().objects.filter(last_modified_by_user__isnull=False).only('last_modified_by_user__id')\
            .distinct().values_list('last_modified_by_user__id', flat=True)
        return get_user_model().objects.filter(id__in=last_modified_by_user_ids)


class CreatedByUserFilter(BaseFilter):
    title = _('created by')
    parameter_name = 'created_by_user'
    field_path = 'created_by_user'
    
    def get_lookup_qs(self, request, model_admin):
        created_by_user_ids = get_user_model().objects.filter(last_modified_by_user__isnull=False).only('created_by_user__id')\
            .distinct().values_list('created_by_user__id', flat=True)
        return get_user_model().objects.filter(id__in=created_by_user_ids)
       

class UserAssociatedSystemFilter(BaseFilter):
    title = _('associated system')
    parameter_name = 'associated_system'
    field_path = 'userassociatedsystem__application'

    def get_lookup_qs(self, request, model_admin):
        return Application.objects.filter(userassociatedsystem__application__isnull=False).distinct()
        

class UserOrganisationsListFilter(OrganisationsListFilter):
    field_path = 'organisations'

    def get_lookup_qs(self, request, model_admin):
        return request.user.get_administrable_organisations()
        

class UserRegionListFilter(BaseFilter):
    """
    Fiter for user admin
    """
    title = _('Region')
    parameter_name = 'region'
    field_path = 'organisations__region'
    
    def get_lookup_qs(self, request, model_admin):
        return Region.objects.all()
    
class ApplicationRolesFilter(BaseFilter):
    """
    Fiter for user admin
    """
    title = _('Application Roles')
    parameter_name = 'application_role'
    field_path = 'application_roles'

    def get_lookup_qs(self, request, model_admin):
        return request.user.get_inheritable_application_roles()


class SuperuserFilter(SimpleListFilter):
    title = _('superuser status')
    parameter_name = 'is_superuser__exact'

    def lookups(self, request, model_admin):
        user = request.user
        if user.is_superuser:
            return [('True', _('Yes')), ('False', _('No'))]
        else:
            return []
    
    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(is_superuser=True)
        elif self.value() == 'False':
            return queryset.filter(is_superuser=False)
        else:
            return queryset.all()
    

class UserAssociatedSystemInline(admin.StackedInline):
    model = UserAssociatedSystem
    fk_name = 'user'
    extra = 0
    fieldsets = ((None, {'fields': (('application', 'userid'),), 'classes': ['wide']}),)
    readonly_fields = ('application', 'userid')
    
    def has_add_permission(self, request):
            return False

class GroupAdmin(DjangoGroupAdmin):
    """
    display wide_ex select widgets
    """
    fieldsets = (
        (None, {'fields': ('name', 'permissions'), 'classes': ['wide', 'wide_ex']}),
    )


class UserAdmin(AdminImageMixin, DjangoUserAdmin):
    form = AdminUserChangeForm
    add_form = UserCreationForm
    list_display = ('id',) + DjangoUserAdmin.list_display + ('last_login', 'date_joined', 'get_last_modified_by_user', 'get_created_by_user')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'uuid')
    list_filter = (SuperuserFilter, ) + ('is_staff', 'is_active', 'groups', UserAssociatedSystemFilter, UserRegionListFilter,
                    ApplicationRolesFilter, LastModifiedUserFilter, CreatedByUserFilter, UserOrganisationsListFilter)
    filter_horizontal = DjangoUserAdmin.filter_horizontal + ('groups', 'application_roles', 'organisations')
    ordering = ['-last_login', '-first_name', '-last_name']
    actions = ['mark_info_mail']
    
    fieldsets = (
        (None, {'fields': ('username', 'password'), 'classes': ['wide']}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'uuid', 'is_center', 'is_subscriber', 'picture'), 'classes': ['wide']}),
        (_('AppRoles'), {'fields': ('assigned_organisations', 'organisations', 'application_roles'), 'classes': ['wide', 'wide_ex']}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'), 'classes': ['wide', 'wide_ex']}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'get_last_modified_by_user', 'get_created_by_user'), 'classes': ['wide']}),
    )
    non_su_fieldsets = (
        (None, {'fields': ('username', ), 'classes': ['wide']}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'uuid', 'is_center', 'is_subscriber'), 'classes': ['wide']}),
        (_('AppRoles'), {'fields': ('is_active', 'assigned_organisations', 'organisations', 'application_roles'), 'classes': ['wide', 'wide_ex']}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'get_last_modified_by_user', 'get_created_by_user'), 'classes': ['wide']}),
    )
    readonly_fields = ['assigned_organisations', 'is_subscriber', 'get_last_modified_by_user', 'get_created_by_user']
    non_su_readonly_fields = ['uuid', 'assigned_organisations', 'is_subscriber', 'username', 'last_login', 'date_joined', 'get_last_modified_by_user', 'get_created_by_user']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'password1', 'password2')}
        ),
    )

    @classmethod
    def merge_allowed_values(cls, form, field_name, allowed_values):
        # if this is a new userprofile, there are no values to merge
        if form.instance.pk is None:
            return
        
        # get the form data and make a set from it
        data = form.cleaned_data[field_name]
        new_data = set(data)
        
        manager = getattr(form.instance, field_name)
        ext_data = set(manager.exclude(id__in=allowed_values.values_list('id', flat=True)))
        
        # merge the 2 data sets
        form.cleaned_data[field_name] = (ext_data | new_data)

    def assigned_organisations(self, obj):
        if obj:
            return u', '.join([x.__unicode__() for x in obj.organisations.all()])

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        user = request.user
        if user.is_superuser:
            return super(UserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)
        
        # use the application_roles from application_roles of the authenticated user        
        if db_field.name == "application_roles":
            kwargs["queryset"] = user.get_inheritable_application_roles()

        if db_field.name == "organisations":
            kwargs["queryset"] = user.get_administrable_organisations()
            
        return super(UserAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_last_modified_by_user(self, obj):
        if obj.last_modified_by_user:
            url = urlresolvers.reverse('admin:accounts_user_change', args=(obj.last_modified_by_user.pk,), current_app=self.admin_site.name)
            return mark_safe(u'<a href="%s">%s</a>' % (url, obj.last_modified_by_user))
        else:
            raise ObjectDoesNotExist()
    get_last_modified_by_user.short_description = _('last modified by')
    get_last_modified_by_user.allow_tags = True
    
    def get_created_by_user(self, obj):
        if obj.created_by_user:
            url = urlresolvers.reverse('admin:accounts_user_change', args=(obj.created_by_user.pk,), current_app=self.admin_site.name)
            return mark_safe(u'<a href="%s">%s</a>' % (url, obj.created_by_user))
        else:
            raise ObjectDoesNotExist()
    get_created_by_user.short_description = _('created by')
    get_created_by_user.allow_tags = True

    def get_actions(self, request):
        """
        remove some actions if the user is not superuser or
        has not the required permissions
        """
        actions = super(UserAdmin, self).get_actions(request)
        user = request.user
        if not user.is_superuser:
            actions.pop('mark_info_mail')
        if not user.has_perm('auth.delete_user'):
            actions.pop('delete_selected')
        return actions
    
    def get_formsets(self, request, obj=None):
        """
        return no inline formsets in the add_view, because the UserProfile is created by
        the post_save signal
        """
        if obj is None:
            return []
        else:
            return super(UserAdmin, self).get_formsets(request, obj)

    def save_formset(self, request, form, formset, change):
        if not request.user.is_superuser:
            # add the application_roles wich were excluded in formfield_for_manytomany
            user_profile_form = formset.forms[0]
            user = request.user
            self.merge_allowed_values(user_profile_form, 'application_roles',
                                                  user.get_inheritable_application_roles())
            self.merge_allowed_values(user_profile_form, 'organisations',
                                                  user.get_administrable_organisations())
        return super(UserAdmin, self).save_formset(request, form, formset, change)
        
    def get_fieldsets(self, request, obj=None):
        """
        removed user_permissions and is_superuser for normal admins,
        permissions should be managed via groups
        """
        if request.user.is_superuser or obj is None:
            return super(UserAdmin, self).get_fieldsets(request, obj)
        else:
            return self.non_su_fieldsets

    def get_form(self, request, obj=None, **kwargs):
        if request.user.is_superuser or obj is None:
            return super(UserAdmin, self).get_form(request, obj, **kwargs)
        else:
            defaults = {}
            defaults.update({
                'form': BasicUserChangeForm,
                'fields': admin.util.flatten_fieldsets(self.non_su_fieldsets),
            })
            defaults.update(kwargs)
            return super(UserAdmin, self).get_form(request, obj, **defaults)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return super(UserAdmin, self).get_readonly_fields(request, obj)
        else:
            return self.non_su_readonly_fields
                   
    def queryset(self, request):
        """
        display no superusers in the changelist for non superusers
        """
        qs = super(UserAdmin, self).queryset(request).select_related('last_modified_by',
                                                                     'created_by')
        user = request.user
        if user.is_superuser:
            return qs
        else:
            if user.has_perm("accounts.change_all_users"):
                return qs.filter(is_superuser=False)
            else:
                organisations = user.get_administrable_organisations()
                q = Q(is_superuser=False) & (
                    Q(organisations__in=organisations))
                return  qs.filter(q).distinct()
                        
    def mark_info_mail(self, request, queryset):
        
        if request.POST.get('post') and request.POST.get('body'):
            n = queryset.count()
            subject = request.POST.get('subject', _('%s SSO Information') % settings.BRAND)
            body = request.POST.get('body')
            from_email = request.POST.get('from_email', None)
            if n:
                from django.core.mail import get_connection
                connection = get_connection()
                for user in queryset:
                    msg = EmailMessage(subject, body, to=[user.email], from_email=from_email, connection=connection)
                    #msg.content_subtype = "html"
                    msg.send(fail_silently=True)
                self.message_user(request, _("Successfully send Information Email to  %(count)d %(items)s.") % {
                    "count": n, "items": model_ngettext(self.opts, n)
                })
            # Return None to display the change list page again.
            return None
        
        opts = self.model._meta
        app_label = opts.app_label
        if len(queryset) == 1:
            objects_name = force_unicode(opts.verbose_name)
        else:
            objects_name = force_unicode(opts.verbose_name_plural)
        
        context = {
            "title": _('Send information mail to selected users'),
            "objects_name": objects_name,
            'queryset': queryset,
            "opts": opts,
            "app_label": app_label,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
        }
        # Display the confirmation page
        return TemplateResponse(request, "admin/accounts/send_mail_selected_confirmation.html", context, current_app=self.admin_site.name)
    mark_info_mail.short_description = _('Send info email')
   

admin.site.register(Group, GroupAdmin)
admin.site.register(get_user_model(), UserAdmin)
admin.site.register(ApplicationRole, ApplicationRoleAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Organisation, OrganisationAdmin)
admin.site.register(Region, RegionAdmin)
