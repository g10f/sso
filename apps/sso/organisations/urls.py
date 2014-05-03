from django.conf.urls import patterns, url
import views
 
urlpatterns = patterns('',
    url(r'^$', views.OrganisationList.as_view(), name='organisation_list'), 
    url(r'^(?P<uuid>[a-z0-9]{32})/$', views.OrganisationDetailView.as_view(), name='organisation_detail'),
    url(r'^(?P<uuid>[a-z0-9]{32})/update/$', views.OrganisationUpdateView.as_view(), name='organisation_update'),
    url(r'^(?P<uuid>[a-z0-9]{32})/delete/$', views.OrganisationDeleteView.as_view(), name='organisation_delete'),
    url(r'^create/$', views.OrganisationCreateView.as_view(), name='organisation_create'),
)
