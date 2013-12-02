from django.conf.urls import patterns, url
import views
 
urlpatterns = patterns('',
    url(r'^v1/$', views.get_index, name='v1_index'),
    url(r'^v1/users/$', views.get_user_list, name='v1_users'),
    url(r'^v1/users/me/$', views.UserDetailView.as_view(), name='v1_users_me'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/$', views.UserDetailView.as_view(), name='v1_user'),
    url(r'^v1/users/me/apps/$', views.UserDetailView.as_view(is_apps_only=True), name='v1_users_my_apps'),
    url(r'^v1/users/(?P<uuid>[a-z0-9]{32})/apps/$', views.UserDetailView.as_view(is_apps_only=True), name='v1_users_apps'),
)
