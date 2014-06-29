# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from sso.auth.forms import EmailAuthenticationForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

from sso.accounts.admin import *
from sso.oauth2.admin import *
from sso.registration.admin import *
from sso.accounts.models import *
from sso.organisations import models as org_models
from sso.organisations import admin as org_admin

from l10n.admin import *
from streaming.admin import *

class SSOAdminSite(admin.AdminSite):
    login_form = EmailAuthenticationForm
    login_template = 'accounts/login.html'


sso_admin_site = SSOAdminSite()

sso_admin_site.register(Group, GroupAdmin)
sso_admin_site.register(get_user_model(), UserAdmin)
sso_admin_site.register(ApplicationRole, ApplicationRoleAdmin)
sso_admin_site.register(RoleProfile, RoleProfileAdmin)
sso_admin_site.register(Role, RoleAdmin)
sso_admin_site.register(Application, ApplicationAdmin)

sso_admin_site.register(AuthorizationCode, AuthorizationCodeAdmin)
sso_admin_site.register(BearerToken, BearerTokenAdmin)
sso_admin_site.register(RefreshToken, RefreshTokenAdmin)
sso_admin_site.register(Client, ClientAdmin)

sso_admin_site.register(Country, CountryOptions)

if 'streaming' in settings.DATABASES:
    sso_admin_site.register(StreamingUser, StreamingUserAdmin)
    sso_admin_site.register(Logging, LoggingAdmin)

sso_admin_site.register(RegistrationProfile, RegistrationAdmin)
sso_admin_site.register(org_models.Organisation, org_admin.OrganisationAdmin)
sso_admin_site.register(org_models.AdminRegion, org_admin.AdminRegionAdmin)
sso_admin_site.register(org_models.OrganisationCountry, org_admin.OrganisationCountryAdmin)
