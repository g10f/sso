# -*- coding: utf-8 -*-
from sso.auth.forms import EmailAuthenticationForm

from sso.accounts.admin import *
from sso.oauth2.admin import *
from sso.registration.admin import *
from sso.accounts import models
from sso.organisations import models as org_models
from sso.organisations import admin as org_admin

from sso.emails.models import Email, EmailForward, EmailAlias, GroupEmail, GroupEmailManager
from sso.emails.admin import EmailAdmin, EmailAliasAdmin, EmailForwardAdmin, GroupEmailAdmin, GroupEmailManagerAdmin

from l10n.admin import *


class SSOAdminSite(admin.AdminSite):
    login_form = EmailAuthenticationForm
    login_template = 'accounts/login.html'


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

sso_admin_site.register(AuthorizationCode, AuthorizationCodeAdmin)
sso_admin_site.register(BearerToken, BearerTokenAdmin)
sso_admin_site.register(RefreshToken, RefreshTokenAdmin)
sso_admin_site.register(Client, ClientAdmin)

sso_admin_site.register(Country, CountryOptions)
sso_admin_site.register(CountryCallingCode, CountryCallingCodeOptions)

sso_admin_site.register(RegistrationProfile, RegistrationAdmin)
sso_admin_site.register(org_models.Organisation, org_admin.OrganisationAdmin)
sso_admin_site.register(org_models.AdminRegion, org_admin.AdminRegionAdmin)
sso_admin_site.register(org_models.OrganisationCountry, org_admin.OrganisationCountryAdmin)
sso_admin_site.register(org_models.CountryGroup, org_admin.CountryGroupAdmin)


sso_admin_site.register(Email, EmailAdmin)
sso_admin_site.register(EmailAlias, EmailAliasAdmin)
sso_admin_site.register(EmailForward, EmailForwardAdmin)
sso_admin_site.register(GroupEmail, GroupEmailAdmin)
sso_admin_site.register(GroupEmailManager, GroupEmailManagerAdmin)
