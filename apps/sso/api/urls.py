from django.conf.urls import patterns, url
from sso.api.views import users, users_v2, organisations, home, emails, countries, regions, country_groups, media
 
urlpatterns = patterns(
    '',
    url(r'^$', home.home, name='home'),
    url(r'^emails.(?P<type>(txt|csv))$', emails.emails, name='emails'),
    url(r'^emails.csv$', emails.emails, name='emails'),
    url(r'^v1/users/$', users.get_user_list, name='v1_users'),
    url(r'^v1/users/me/$', users.UserDetailView.as_view(), name='v1_users_me'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/$', users.UserDetailView.as_view(), name='v1_user'),
    url(r'^v1/users/me/apps/$', users.UserDetailView.as_view(is_apps_only=True), name='v1_users_my_apps'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/apps/$', users.UserDetailView.as_view(is_apps_only=True), name='v1_users_apps'),
    url(r'^v2/users/$', users_v2.UserList.as_view(), name='v2_users'),
    url(r'^v2/users/me/$', users_v2.MyDetailView.as_view(), name='v2_users_me'),
    url(r'^v2/users/(?P<uuid>[a-z0-9]{32})/$', users_v2.UserDetailView.as_view(), name='v2_user'),
    url(r'^v2/users/me/navigation/$', users_v2.MyGlobalNavigationView.as_view(), name='v2_navigation_me'),
    url(r'^v2/users/(?P<uuid>[a-z0-9]{32})/navigation/$', users_v2.GlobalNavigationView.as_view(), name='v2_navigation'),
    url(r'^v2/organisations/$', organisations.OrganisationList.as_view(), name='v2_organisations'),
    url(r'^v2/organisations/(?P<uuid>[a-z0-9]{32})/$', organisations.OrganisationDetailView.as_view(), name='v2_organisation'),
    url(r'^v2/countries/$', countries.CountryList.as_view(), name='v2_countries'),
    url(r'^v2/countries/(?P<iso2_code>[A-Z]{2})/$', countries.CountryDetailView.as_view(), name='v2_country'),
    url(r'^v2/regions/$', regions.RegionList.as_view(), name='v2_regions'),
    url(r'^v2/regions/(?P<uuid>[a-z0-9]{32})/$', regions.RegionDetailView.as_view(), name='v2_region'),
    url(r'^v2/country_groups/$', country_groups.CountryGroupList.as_view(), name='v2_country_groups'),
    url(r'^v2/country_groups/(?P<uuid>[a-z0-9]{32})/$', country_groups.CountryGroupDetailView.as_view(), name='v2_country_group'), 
    url(r'^v2/users/me/picture/$', media.MyUserPictureDetailView.as_view(), name='v2_picture_me'),
    url(r'^v2/users/(?P<uuid>[a-z0-9]{32})/picture/$', media.UserPictureDetailView.as_view(), name='v2_picture'),
)
