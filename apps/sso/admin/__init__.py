from functools import update_wrapper
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.utils.translation import ugettext_lazy as _
from sso.accounts.admin import ApplicationAdmin, ApplicationAdminAdmin, ApplicationRoleAdmin, GroupAdmin, RoleAdmin, \
    OneTimeMessageAdmin, OrganisationChangeAdmin, RoleProfileAdmin, RoleProfileAdminAdmin, UserAdmin, UserEmailAdmin
from sso.auth.utils import is_recent_auth_time
from sso.oauth2.admin import ClientAdmin, AuthorizationCodeAdmin, BearerTokenAdmin, RefreshTokenAdmin
from sso.oauth2.models import Client, AuthorizationCode, BearerToken, RefreshToken
from sso.registration.admin import RegistrationAdmin
from sso.registration.models import RegistrationProfile
from sso.emails.models import Email, EmailForward, EmailAlias, GroupEmail, GroupEmailManager
from sso.emails.admin import EmailAdmin, EmailAliasAdmin, EmailForwardAdmin, GroupEmailAdmin, GroupEmailManagerAdmin
from l10n.admin import CountryOptions
from l10n.models import Country
from sso.accounts import models
from sso.organisations import models as org_models
from sso.organisations import admin as org_admin
from sso.auth import models as sso_auth_models
from sso.auth import admin as sso_auth_admin
from sso.utils.translation import string_format


class SSOAdminSite(admin.AdminSite):
    """
    copy of django admin view with:
    - redirecting to accounts:login instead of admin:login
    """
    site_title = string_format(_('%(brand)s SSO site admin') , {'brand': settings.SSO_BRAND})
    site_header = string_format(_('%(brand)s SSO administration'), {'brand': settings.SSO_BRAND})

    def admin_view(self, view, cacheable=False):
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                if request.path == reverse('admin:logout', current_app=self.name):
                    index_path = reverse('admin:index', current_app=self.name)
                    return HttpResponseRedirect(index_path)
                # Inner import to prevent django.contrib.admin (app) from
                # importing django.contrib.auth.models.User (unrelated model).
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(
                    request.get_full_path(),
                    reverse('auth:login')
                )
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)

    @never_cache
    def login(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('auth:login'))

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return super(SSOAdminSite, self).has_permission(request) and is_recent_auth_time(request)


sso_admin_site = SSOAdminSite()

sso_admin_site.register(models.Group, GroupAdmin)
sso_admin_site.register(models.OneTimeMessage, OneTimeMessageAdmin)

# sso_admin_site.register(Permission, PermissionAdmin)
# sso_admin_site.register(ContentType)

sso_admin_site.register(models.UserEmail, UserEmailAdmin)
sso_admin_site.register(get_user_model(), UserAdmin)
sso_admin_site.register(models.ApplicationRole, ApplicationRoleAdmin)
sso_admin_site.register(models.RoleProfile, RoleProfileAdmin)
sso_admin_site.register(models.Role, RoleAdmin)
sso_admin_site.register(models.Application, ApplicationAdmin)
sso_admin_site.register(models.ApplicationAdmin, ApplicationAdminAdmin)
sso_admin_site.register(models.RoleProfileAdmin, RoleProfileAdminAdmin)
sso_admin_site.register(models.OrganisationChange, OrganisationChangeAdmin)

sso_admin_site.register(AuthorizationCode, AuthorizationCodeAdmin)
sso_admin_site.register(BearerToken, BearerTokenAdmin)
sso_admin_site.register(RefreshToken, RefreshTokenAdmin)
sso_admin_site.register(Client, ClientAdmin)

sso_admin_site.register(Country, CountryOptions)

sso_admin_site.register(RegistrationProfile, RegistrationAdmin)
sso_admin_site.register(org_models.Organisation, org_admin.OrganisationAdmin)
sso_admin_site.register(org_models.AdminRegion, org_admin.AdminRegionAdmin)
sso_admin_site.register(org_models.OrganisationCountry, org_admin.OrganisationCountryAdmin)
sso_admin_site.register(org_models.CountryGroup, org_admin.CountryGroupAdmin)
sso_admin_site.register(org_models.Association, org_admin.AssociationAdmin)


sso_admin_site.register(Email, EmailAdmin)
sso_admin_site.register(EmailAlias, EmailAliasAdmin)
sso_admin_site.register(EmailForward, EmailForwardAdmin)
sso_admin_site.register(GroupEmail, GroupEmailAdmin)
sso_admin_site.register(GroupEmailManager, GroupEmailManagerAdmin)

sso_admin_site.register(sso_auth_models.Profile, sso_auth_admin.ProfileAdmin)
sso_admin_site.register(sso_auth_models.Device, sso_auth_admin.DeviceAdmin)
sso_admin_site.register(sso_auth_models.TwilioSMSDevice, sso_auth_admin.TwilioSMSDeviceAdmin)
sso_admin_site.register(sso_auth_models.TOTPDevice, sso_auth_admin.TOTPDeviceAdmin)
sso_admin_site.register(sso_auth_models.U2FDevice, sso_auth_admin.U2FDeviceAdmin)
