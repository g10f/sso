from django.urls import path
from sso.api.views import users, users_v2, organisations, home, countries, regions, country_groups, media, associations

app_name = 'api'

urlpatterns = [
    path('', home.home, name='home'),
    path('user_emails/', users_v2.user_emails, name='user_emails'),
    path('v1/users/', users.get_user_list, name='v1_users'),
    path('v1/users/me/', users.UserDetailView.as_view(), name='v1_users_me'),
    path('v1/users/<uuid:uuid>/', users.UserDetailView.as_view(), name='v1_user'),
    path('v1/users/me/apps/', users.UserDetailView.as_view(is_apps_only=True), name='v1_users_my_apps'),
    path('v1/users/<uuid:uuid>/apps/', users.UserDetailView.as_view(is_apps_only=True),
         name='v1_users_apps'),
    path('v2/users/', users_v2.UserList.as_view(), name='v2_users'),
    path('v2/users/me/', users_v2.MyDetailView.as_view(), name='v2_users_me'),
    path('v2/users/<uuid:uuid>/', users_v2.UserDetailView.as_view(), name='v2_user'),
    path('v2/users/me/navigation/', users_v2.MyGlobalNavigationView.as_view(), name='v2_navigation_me'),
    path('v2/users/<uuid:uuid>/navigation/', users_v2.GlobalNavigationView.as_view(),
         name='v2_navigation'),
    path('v2/organisations/', organisations.OrganisationList.as_view(), name='v2_organisations'),
    path('v2/organisations/<uuid:uuid>/', organisations.OrganisationDetailView.as_view(),
         name='v2_organisation'),
    path('v2/countries/', countries.CountryList.as_view(), name='v2_countries'),
    path('v2/countries/<slug:iso2_code>/', countries.CountryDetailView.as_view(), name='v2_country'),
    path('v2/regions/', regions.RegionList.as_view(), name='v2_regions'),
    path('v2/regions/<uuid:uuid>/', regions.RegionDetailView.as_view(), name='v2_region'),
    path('v2/country_groups/', country_groups.CountryGroupList.as_view(), name='v2_country_groups'),
    path('v2/country_groups/<uuid:uuid>/', country_groups.CountryGroupDetailView.as_view(),
         name='v2_country_group'),
    path('v2/associations/', associations.AssociationList.as_view(), name='v2_associations'),
    path('v2/associations/<uuid:uuid>/', associations.AssociationDetailView.as_view(),
         name='v2_association'),
    path('v2/users/me/picture/', media.MyUserPictureDetailView.as_view(), name='v2_picture_me'),
    path('v2/users/<uuid:uuid>/picture/', media.UserPictureDetailView.as_view(), name='v2_picture'),
]
