from django.conf.urls import url
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView
from django.views.generic import TemplateView
from .views import PasswordResetView, PasswordResetConfirmView, PasswordChangeDoneView, PasswordCreateConfirmView
from .views import application, PasswordCreateCompleteView
from .views import emails, confirm_email
from .views import onetimemessage
from .views import organisation
from .views import password_change, logout, profile, contact, delete_profile

app_name = 'accounts'

urlpatterns = [
    url(r'^$', application.UserList.as_view(), name='user_list'),
    url(r'^me/$', profile, name='profile'),
    url(r'^add/$', application.add_user, name='add_user'),
    url(r'^add/done/(?P<uuid>[^/]+)/$', application.add_user_done, name="add_user_done"),
    url(r'^(?P<uuid>[a-z0-9]{32})/$', application.update_user, name="update_user"),
    url(r'^(?P<uuid>[a-z0-9]{32})/delete/$', application.UserDeleteView.as_view(), name="delete_user"),
    url(r'^app_admin/$', application.AppAdminUserList.as_view(), name='app_admin_user_list'),
    url(r'^app_admin/(?P<uuid>[a-z0-9]{32})/', application.app_admin_update_user, name="app_admin_update_user"),
    url(r'^logout/$', logout, name='logout'),
    url(r'^contact/$', contact, name='contact'),
    url(r'^contact_thanks/$', TemplateView.as_view(template_name="accounts/contact_thanks.html"),
        name='contact_thanks'),
    url(r'^email/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', confirm_email,
        name='confirm_email'),
    url(r'^emails/$', emails, name='emails'),
    url(r'^profile/delete/$', delete_profile, name='delete_profile'),
    url(r'^password_change/$', password_change, name='password_change'),
    url(r'^password_change/done/$', PasswordChangeDoneView.as_view(), name='password_change_done'),
    url(r'^password_reset/$', PasswordResetView.as_view(), name='password_reset'),
    url(r'^password_reset/done/$', PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done'),
    url(r'^password_resend/done/$', TemplateView.as_view(template_name="accounts/password_resend_done.html"),
        name='password_resend_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'^reset/done/$', PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete'),
    url(r'^create/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordCreateConfirmView.as_view(), name='password_create_confirm'),
    url(r'^create/done/(?P<uidb64>[0-9A-Za-z_\-]+)/$', PasswordCreateCompleteView.as_view(),
        name='password_create_complete'),
    url(r'^organisation_change/(?P<pk>\d+)/$', organisation.OrganisationChangeDetailView.as_view(),
        name='organisationchange_detail'),
    url(r'^organisation_change/me/$', organisation.OrganisationChangeUpdateView.as_view(),
        name='organisationchange_me'),
    url(r'^organisation_change/$', organisation.OrganisationChangeList.as_view(), name='organisationchange_list'),
    url(r'^organisation_change/(?P<pk>\d+)/accept/$', organisation.OrganisationChangeAcceptView.as_view(),
        name='organisationchange_accept'),
    url(r'^messages/(?P<uuid>[^/]+)/$', onetimemessage.OneTimeMessageView.as_view(), name="view_message"),
]
