from django.conf.urls import patterns, url
from sso.emails import views
 
urlpatterns = patterns(
    '',
    url(r'^$', views.EmailList.as_view(), name='email_list'), 
    url(r'^(?P<uuid>[a-z0-9]{32})/update/$', views.EmailUpdateView.as_view(), name='email_update'),
)
