from django.conf.urls import patterns, url
from sso.api.views import users
 
urlpatterns = patterns(
    '',
    url(r'^v1/users/$', users.get_user_list, name='v1_users'),
    url(r'^v1/users/me/$', users.UserDetailView.as_view(), name='v1_users_me'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/$', users.UserDetailView.as_view(), name='v1_user'),
    url(r'^v1/users/me/apps/$', users.UserDetailView.as_view(is_apps_only=True), name='v1_users_my_apps'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/apps/$', users.UserDetailView.as_view(is_apps_only=True), name='v1_users_apps'),
)
