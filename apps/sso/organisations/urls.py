from django.conf.urls import url
from . import views
from .views import region, country
 
urlpatterns = [
    url(r'^$', views.OrganisationList.as_view(), name='organisation_list'),
    url(r'^export.csv$', views.OrganisationList.as_view(export=True, filename="organisations.csv", content_type='text/csv;charset=utf-8;'), name='organisation_list_csv'),
    url(r'^export.txt$', views.OrganisationList.as_view(export=True, content_type='text;charset=utf-8;'), name='organisation_list_txt'),
    url(r'^me/$', views.MyOrganisationDetailView.as_view(), name='my_organisation_detail'),
    url(r'^(?P<uuid>[a-z0-9]{32})/$', views.OrganisationDetailView.as_view(), name='organisation_detail'),
    url(r'^(?P<uuid>[a-z0-9]{32})/update/$', views.OrganisationUpdateView.as_view(), name='organisation_update'),
    url(r'^(?P<uuid>[a-z0-9]{32})/delete/$', views.OrganisationDeleteView.as_view(), name='organisation_delete'),
    url(r'^(?P<uuid>[a-z0-9]{32})/picture/$', views.OrganisationPictureUpdateView.as_view(), name='organisation_picture_update'),
    url(r'^add/$', views.OrganisationCreateView.as_view(), name='organisation_create'),
    url(r'^region/$', region.AdminRegionList.as_view(), name='adminregion_list'), 
    url(r'^region/(?P<uuid>[a-z0-9]{32})/$', region.AdminRegionDetailView.as_view(), name='adminregion_detail'),
    url(r'^region/(?P<uuid>[a-z0-9]{32})/update/$', region.AdminRegionUpdateView.as_view(), name='adminregion_update'),
    url(r'^region/add/$', region.AdminRegionCreateView.as_view(), name='adminregion_create'),
    url(r'^country/$', country.OrganisationCountryList.as_view(), name='organisationcountry_list'), 
    url(r'^country/(?P<uuid>[a-z0-9]{32})/$', country.OrganisationCountryDetailView.as_view(), name='organisationcountry_detail'),
    url(r'^country/(?P<uuid>[a-z0-9]{32})/update/$', country.OrganisationCountryUpdateView.as_view(), name='organisationcountry_update'),
    url(r'^country/add/$', country.OrganisationCountryCreateView.as_view(), name='organisationcountry_create'),
]
