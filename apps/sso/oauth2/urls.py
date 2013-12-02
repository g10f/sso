from django.conf.urls import patterns, url
import views
 
urlpatterns = patterns('',
    url(r'^client/(?P<object_id>.+)/$', views.client_details, name='client.details.json'),
    url(r'^authorize/$', views.authorize, name='authorize'),
    url(r'^certs/$', views.certs, name='certs'),
    url(r'^token/$', views.token, name='token'),
    url(r'^approval/$', views.approval, name='approval'),
    url(r'^error/$', views.ErrorView.as_view(), name='oauth2_error'),
)
