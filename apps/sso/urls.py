from django.apps import apps

from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.views.i18n import JavaScriptCatalog
from smart_selects.views import filterchain
from sso.accounts.forms import UserSelfRegistrationForm2
from sso.admin import sso_admin_site
from sso.oauth2.views import OpenidConfigurationView
from sso.registration.sites import RegistrationSite
from sso.views import home

registration_site = RegistrationSite(form_cls=UserSelfRegistrationForm2)

urlpatterns = [
    url(r'^jsi18n/$', JavaScriptCatalog.as_view(packages=['sso']), name='jsi18n'),
    url(r'^admin/', sso_admin_site.urls),
    url(r'^$', home, name='home'),
    url(r'^privacy/$', TemplateView.as_view(template_name="privacy.html"), name='privacy'),
    url(r'^about/$', RedirectView.as_view(url=settings.SSO_ABOUT, permanent=False), name='about'),
    url(r'^accounts/', include('sso.auth.urls')),
    url(r'^accounts/', include('sso.accounts.urls')),
    url(r'^accounts/', registration_site.urls),
    url(r'^organisations/', include('sso.organisations.urls')),
    url(r'^emails/', include('sso.emails.urls')),
    url(r'^oauth2/', include('sso.oauth2.urls')),
    url(r'^.well-known/openid-configuration', OpenidConfigurationView.as_view(),
        name='openid-configuration'),
    url(r'^api/', include('sso.api.urls')),
    url(r'^chained_filter/(?P<app>l10n)/(?P<model>[\w\-]+)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$', filterchain,
        name='chained_filter'),
    url(r'^chained_filter/(?P<app>organisations)/(?P<model>OrganisationCountry)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$',
        filterchain, kwargs={'manager': 'active_objects'}, name='chained_filter'),
    url(r'^chained_filter/(?P<app>organisations)/(?P<model>AdminRegion)/(?P<field>[\w\-]+)/(?P<value>[\w\-]+)/$',
        filterchain, kwargs={'manager': 'active_objects'}, name='chained_filter'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed('sso.access_requests'):
    urlpatterns += [
        url(r'^extend_access/', include('sso.access_requests.urls')),
    ]
