from django.urls import path
from . import views
from .views import region, country

app_name = 'organisations'

urlpatterns = [
    path('', views.OrganisationList.as_view(), name='organisation_list'),
    path('export.csv', views.OrganisationList.as_view(export=True, filename="organisations.csv", content_type='text/csv;charset=utf-8;'),
         name='organisation_list_csv'),
    path('export.txt', views.OrganisationList.as_view(export=True, content_type='text;charset=utf-8;'), name='organisation_list_txt'),
    path('me/', views.MyOrganisationDetailView.as_view(), name='my_organisation_detail'),
    path('<uuid:uuid>/', views.OrganisationDetailView.as_view(), name='organisation_detail'),
    path('<uuid:uuid>/update/', views.OrganisationUpdateView.as_view(), name='organisation_update'),
    path('<uuid:uuid>/delete/', views.OrganisationDeleteView.as_view(), name='organisation_delete'),
    path('<uuid:uuid>/picture/', views.OrganisationPictureUpdateView.as_view(), name='organisation_picture_update'),
    path('add/', views.OrganisationCreateView.as_view(), name='organisation_create'),
    path('region/', views.region.AdminRegionList.as_view(), name='adminregion_list'),
    path('region/<uuid:uuid>/', region.AdminRegionDetailView.as_view(), name='adminregion_detail'),
    path('region/<uuid:uuid>/update/', region.AdminRegionUpdateView.as_view(), name='adminregion_update'),
    path('region/add/', region.AdminRegionCreateView.as_view(), name='adminregion_create'),
    path('country/', country.OrganisationCountryList.as_view(), name='organisationcountry_list'),
    path('country/<uuid:uuid>/', country.OrganisationCountryDetailView.as_view(), name='organisationcountry_detail'),
    path('country/<uuid:uuid>/update/', country.OrganisationCountryUpdateView.as_view(), name='organisationcountry_update'),
    path('country/add/', country.OrganisationCountryCreateView.as_view(), name='organisationcountry_create'),
]
