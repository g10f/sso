import sso
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, register_converter
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import last_modified
from django.views.generic import RedirectView, TemplateView
from django.views.i18n import JavaScriptCatalog
from smart_selects.views import filterchain
from sso.accounts.views.application import get_default_user_self_registration_form_class
from sso.admin import sso_admin_site
from sso.oauth2.views import OpenidConfigurationView
from sso.registration.sites import RegistrationSite
from sso.utils.url import UUIDConverter
from sso.views import home

registration_site = RegistrationSite(form_cls=get_default_user_self_registration_form_class())

register_converter(UUIDConverter, 'uuid')
last_modified_date = timezone.now()

urlpatterns = [
    path('', home, name='home'),
    path('.well-known/openid-configuration', OpenidConfigurationView.as_view(), name='openid-configuration'),
    path('jsi18n/',
         cache_page(60 * 60 * 24, key_prefix='js18n-%s' % sso.__version__)(last_modified(lambda req, **kw: last_modified_date)(JavaScriptCatalog.as_view())),
         name='jsi18n'),
    path('admin/', sso_admin_site.urls),
    path('privacy/', TemplateView.as_view(template_name="privacy.html"), name='privacy'),
    path('about/', RedirectView.as_view(url=settings.SSO_ABOUT, permanent=False), name='about'),
    path('accounts/', include('sso.auth.urls')),
    path('accounts/', include('sso.accounts.urls')),
    path('accounts/', registration_site.urls),
    path('accounts/', include('sso.impersonate.urls')),
    path('organisations/', include('sso.organisations.urls')),
    path('emails/', include('sso.emails.urls')),
    path('oauth2/', include('sso.oauth2.urls')),
    path('api/', include('sso.api.urls')),
    path('chained_filter/organisations/OrganisationCountry/<slug:field>/<slug:value>/', filterchain,
         kwargs={'app': 'organisations', 'model': 'OrganisationCountry', 'manager': 'active_objects'},
         name='chained_filter'),
    path('chained_filter/organisations/AdminRegion/<slug:field>/<slug:value>/', filterchain,
         kwargs={'app': 'organisations', 'model': 'AdminRegion', 'manager': 'active_objects'}, name='chained_filter'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed('sso.access_requests'):
    urlpatterns += [
        path('extend_access/', include('sso.access_requests.urls')),
    ]
