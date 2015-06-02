# -*- coding: utf-8 -*-
from django.conf.urls import url, include
from django.conf import settings
from django.views.generic import RedirectView, TemplateView
from django.views.i18n import javascript_catalog
from django.conf.urls.static import static
from smart_selects.views import filterchain
from sso.accounts.forms import UserSelfRegistrationForm2
from sso.registration.sites import RegistrationSite
from sso.admin import sso_admin_site
from sso.views import home
from sso.oauth2.views import openid_configuration

registration_site = RegistrationSite(form_cls=UserSelfRegistrationForm2)

js_info_dict = {
    'packages': ('sso',),
}

urlpatterns = [
    url(r'^jsi18n/$', javascript_catalog, js_info_dict),
    url(r'^admin/', include(sso_admin_site.urls)),
    url(r'^$', home, name='home'),
    url(r'^privacy/$', TemplateView.as_view(template_name="privacy.html"), name='privacy'),
    url(r'^about/$', RedirectView.as_view(url=settings.SSO_ABOUT, permanent=False), name='about'),
    url(r'^accounts/', include('sso.auth.urls', namespace="auth")),
    url(r'^accounts/', include('sso.accounts.urls', namespace="accounts")),
    url(r'^accounts/', include(registration_site.urls)),
    url(r'^organisations/', include('sso.organisations.urls', namespace="organisations")),
    url(r'^emails/', include('sso.emails.urls', namespace="emails")),
    url(r'^oauth2/', include('sso.oauth2.urls', namespace="oauth2")),
    url(r'^.well-known/openid-configuration', openid_configuration, name='openid-configuration'),
    url(r'^api/', include('sso.api.urls', namespace="api")),
    url(r'^chained_filter/(?P<app>l10n)/(?P<model>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', filterchain, name='chained_filter'),
    url(r'^chained_filter/(?P<app>organisations)/(?P<model>AdminRegion)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', filterchain,
        kwargs={'manager': 'active_objects'}, name='chained_filter'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
