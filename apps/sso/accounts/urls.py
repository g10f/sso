from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from .views import application
from .views import onetimemessage
from .views import password_change, password_change_done, login, logout, profile, contact, delete_profile
from .views import password_reset, password_reset_confirm, password_reset_done, password_reset_complete
from .views import emails, confirm_email, password_create_confirm, password_create_complete
from .views import organisation

urlpatterns = patterns(
    '',
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^contact/$', contact, name='contact'),
    url(r'^contact_thanks/$', TemplateView.as_view(template_name="accounts/contact_thanks.html"), name='contact_thanks'),
    url(r'^profile/$', profile, name='profile'),
    url(r'^email/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', confirm_email, name='confirm_email'),
    url(r'^emails/$', emails, name='emails'),
    url(r'^profile/delete/$', delete_profile, name='delete_profile'),
    url(r'^password_change/$', password_change, name='password_change'),
    url(r'^password_change/done/$', password_change_done, name='password_change_done'),
    url(r'^password_reset/$', password_reset, name='password_reset'),
    url(r'^password_reset/done/$', password_reset_done, name='password_reset_done'),
    url(r'^password_resend/done/$', TemplateView.as_view(template_name="accounts/password_resend_done.html"), name='password_resend_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', password_reset_complete, name='password_reset_complete'),
    url(r'^create/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', password_create_confirm, name='password_create_confirm'),
    url(r'^create/done/$', password_create_complete, name='password_create_complete'),
    url(r'^users/$', application.UserList.as_view(), name='user_list'),
    url(r'^users/add/$', application.add_user, name='add_user'),
    url(r'^users/add/done/(?P<uuid>[^/]+)/$', application.add_user_done, name="add_user_done"),
    url(r'^users/(?P<uuid>[^/]+)/$', application.update_user, name="update_user"),
    url(r'^users/(?P<uuid>[^/]+)/app_roles/', application.update_user_app_roles, name="update_user_app_roles"),
    url(r'^users/(?P<uuid>[^/]+)/delete/$', application.UserDeleteView.as_view(), name="delete_user"),
    url(r'^organisation_change/(?P<pk>\d+)/$', organisation.OrganisationChangeDetailView.as_view(), name='organisationchange_detail'),
    url(r'^organisation_change/(?P<pk>\d+)/update/$', organisation.OrganisationChangeUpdateView.as_view(), name='organisationchange_update'),
    url(r'^organisation_change/create/$', organisation.OrganisationChangeCreateView.as_view(), name='organisationchange_create'),
    url(r'^organisation_change/$', organisation.OrganisationChangeList.as_view(), name='organisationchange_list'),
    url(r'^organisation_change/(?P<pk>\d+)/accept/$', organisation.OrganisationChangeAcceptView.as_view(), name='organisationchange_accept'),
    url(r'^messages/(?P<uuid>[^/]+)/$', onetimemessage.OneTimeMessageView.as_view(), name="view_message"),
)