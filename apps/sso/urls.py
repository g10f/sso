# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.views.generic import RedirectView
from django.conf.urls.static import static
from sso.accounts.forms import UserSelfRegistrationForm2
from sso.registration.sites import RegistrationSite
from sso.admin import sso_admin_site

registration_site = RegistrationSite(form_cls=UserSelfRegistrationForm2)

urlpatterns = patterns(
    '',
    url(r'^admin/', include(sso_admin_site.urls)),
    url(r'^$', 'sso.views.home', name='home'),
    url(r'^about/$', RedirectView.as_view(url=settings.SSO_CUSTOM['ABOUT']), name='about'),
    url(r'^accounts/', include('sso.accounts.urls', namespace="accounts")),
    url(r'^accounts/', include(registration_site.urls)),
    url(r'^organisations/', include('sso.organisations.urls', namespace="organisations")),
    url(r'^emails/', include('sso.emails.urls', namespace="emails")),
    url(r'^oauth2/', include('sso.oauth2.urls', namespace="oauth2")),
    url(r'^.well-known/openid-configuration', 'sso.oauth2.views.openid_configuration', name='openid-configuration'),
    url(r'^.well-known/home', 'sso.api.views.users.home', name='json-home'),
    url(r'^api/', include('sso.api.urls', namespace="api")),
    url(r'^chained_filter/(?P<app>l10n)/(?P<model>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', 'smart_selects.views.filterchain', name='chained_filter'),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
