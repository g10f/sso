# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.views.generic import RedirectView
from django.conf.urls.static import static
from sso.accounts.forms import UserRegistrationCreationForm2
from sso.registration.sites import RegistrationSite
from sso.admin import sso_admin_site

registration_site = RegistrationSite(form_cls=UserRegistrationCreationForm2)

urlpatterns = patterns('',
    url(r'^admin/', include(sso_admin_site.urls)),
    url(r'^$', 'sso.views.home', name='home'),
    url(r'^about/$', RedirectView.as_view(url=settings.ABOUT), name='about'),
    url(r'^accounts/', include('sso.accounts.urls', namespace="accounts")),
    url(r'^accounts/', include(registration_site.urls)),
    url(r'^oauth2/', include('sso.oauth2.urls', namespace="oauth2")),
    url(r'^api/', include('sso.api.urls', namespace="api")),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
