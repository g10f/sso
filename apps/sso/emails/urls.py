from django.conf.urls import url
from sso.emails import views

app_name = 'emails'

urlpatterns = [
    url(r'^group/$', views.GroupEmailList.as_view(), name='groupemail_list'),
    url(r'^group/(?P<uuid>[a-z0-9]{32})/$', views.GroupEmailDetailView.as_view(), name='groupemail_detail'),
    url(r'^group/(?P<uuid>[a-z0-9]{32})/update/$', views.GroupEmailUpdateView.as_view(), name='groupemail_update'),
    url(r'^group/add/$', views.GroupEmailCreateView.as_view(), name='groupemail_create'),
    url(r'^group/(?P<uuid>[a-z0-9]{32})/forward/add/$', views.GroupEmailForwardCreateView.as_view(),
        name='emailforward_create'),
    url(r'^group/(?P<uuid>[a-z0-9]{32})/forward/(?P<pk>\d+)/$', views.GroupEmailForwardDeleteView.as_view(),
        name="emailforward_confirm_delete"),
]
