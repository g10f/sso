from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from .views import application
from .views import onetimemessage
from .views import password_change, password_change_done, login, logout, profile, contact, delete_profile
from .views import password_reset, password_reset_confirm, password_reset_done, password_reset_complete
 
urlpatterns = patterns(
    '',
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^contact/$', contact, name='contact'),
    url(r'^contact_thanks/$', TemplateView.as_view(template_name="accounts/contact_thanks.html"), name='contact_thanks'),
    url(r'^profile/$', profile, name='profile'),
    url(r'^profile/delete/$', delete_profile, name='delete_profile'),
    url(r'^password_change/$', password_change, name='password_change'),
    url(r'^password_change/done/$', password_change_done, name='password_change_done'),
    url(r'^password_reset/$', password_reset, name='password_reset'),
    url(r'^password_reset/done/$', password_reset_done, name='password_reset_done'),
    url(r'^password_resend/done/$', TemplateView.as_view(template_name="accounts/password_resend_done.html"), name='password_resend_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', password_reset_complete, name='password_reset_complete'),
    url(r'^settings/', TemplateView.as_view(template_name="accounts/settings.html"), name="settings"),
    url(r'^application/users/$', application.UserList.as_view(), name='user_list'),
    url(r'^application/users/add/$', application.add_user, name='add_user'),
    url(r'^application/users/add/done/(?P<uuid>[^/]+)/$', application.add_user_done, name="add_user_done"),
    url(r'^application/users/(?P<uuid>[^/]+)/$', application.update_user, name="update_user"), 
    url(r'^application/users/delete/(?P<uuid>[^/]+)/$', application.UserDeleteView.as_view(), name="delete_user"),
    url(r'^messages/(?P<uuid>[^/]+)/$', onetimemessage.OneTimeMessageView.as_view(), name="view_message"), 
)
