from django.conf.urls import url
from . import views

app_name = 'oauth2'

urlpatterns = [
    url(r'^client/(?P<object_id>.+)/$', views.client_details, name='client.details.json'),
    url(r'^authorize/$', views.authorize, name='authorize'),
    url(r'^revoke/$', views.revoke, name='revoke'),
    url(r'^certs/$', views.certs, name='certs'),
    url(r'^jwks/$', views.jwks, name='jwks'),
    url(r'^token/$', views.token, name='token'),
    url(r'^tokeninfo/$', views.tokeninfo, name='tokeninfo'),
    url(r'^approval/$', views.approval, name='approval'),
    url(r'^error/$', views.ErrorView.as_view(), name='oauth2_error'),
    url(r'^session/$', views.SessionView.as_view(template_name="oauth2/session.html"), name='session'),
]
