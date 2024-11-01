from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView
from django.urls import path
from django.views.generic import TemplateView
from .views import PasswordResetView, PasswordResetConfirmView, PasswordChangeDoneView, PasswordCreateConfirmView, \
    application
from .views import account, PasswordCreateCompleteView, usernote
from .views import emails, confirm_email
from .views import onetimemessage
from .views import organisation
from .views import password_change, profile, contact, delete_profile

app_name = 'accounts'

urlpatterns = [
    path('', account.UserList.as_view(), name='user_list'),
    path('me/', profile, name='profile'),
    path('add/', account.add_user, name='add_user'),
    path('add/done/<sso.uuid:uuid>/', account.add_user_done, name="add_user_done"),
    path('<sso.uuid:uuid>/', account.update_user, name="update_user"),
    path('<sso.uuid:uuid>/delete/', account.UserDeleteView.as_view(), name="delete_user"),
    path('<sso.uuid:uuid>/notes/delete/', usernote.UserNoteDeleteView.as_view(), name="delete_user_note"),
    path('app/admin/', account.AppAdminUserList.as_view(), name='app_admin_user_list'),
    path('app/admin/<sso.uuid:uuid>/', account.app_admin_update_user, name="app_admin_update_user"),
    path('app/', application.ApplicationListView.as_view(), name='application_list'),
    path('app/add/', application.ApplicationCreateView.as_view(), name='application_add'),
    path('app/<sso.uuid:uuid>/', application.ApplicationDetailView.as_view(), name='application_detail'),
    path('app/<sso.uuid:uuid>/update/', application.ApplicationUpdateView.as_view(), name='application_update'),
    path('app/<sso.uuid:uuid>/delete/', application.ApplicationDeleteView.as_view(), name='application_delete'),
    path('app/<sso.uuid:uuid>/client/add/', application.ClientCreateView.as_view(), name='client_add'),
    path('app/client/<sso.uuid:uuid>/update/', application.ClientUpdateView.as_view(), name='client_update'),
    path('app/client/<sso.uuid:uuid>/delete/', application.ClientDeleteView.as_view(), name='client_delete'),
    path('app/client/secret/', application.client_secret, name='client_secret'),
    path('contact/', contact, name='contact'),
    path('contact_thanks/', TemplateView.as_view(template_name="accounts/contact_thanks.html"), name='contact_thanks'),
    path('email/confirm/<str:uidb64>/<str:token>/', confirm_email, name='confirm_email'),
    path('emails/', emails, name='emails'),
    path('profile/delete/', delete_profile, name='delete_profile'),
    path('password_change/', password_change, name='password_change'),
    path('password_change/done/', PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('password_resend/done/', TemplateView.as_view(template_name="accounts/password_resend_done.html"), name='password_resend_done'),
    path('reset/done/', PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
    path('reset/<slug:uidb64>/<slug:token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # must be before 'create/<slug:uidb64>/<slug:token>/'
    path('create/done/<slug:uidb64>/', PasswordCreateCompleteView.as_view(), name='password_create_complete'),
    path('create/<slug:uidb64>/<slug:token>/', PasswordCreateConfirmView.as_view(), name='password_create_confirm'),
    path('organisation_change/<int:pk>/', organisation.OrganisationChangeDetailView.as_view(), name='organisationchange_detail'),
    path('organisation_change/me/', organisation.OrganisationChangeUpdateView.as_view(), name='organisationchange_me'),
    path('organisation_change/', organisation.OrganisationChangeList.as_view(), name='organisationchange_list'),
    path('organisation_change/<int:pk>/accept/', organisation.OrganisationChangeAcceptView.as_view(), name='organisationchange_accept'),
    path('messages/<sso.uuid:uuid>/', onetimemessage.OneTimeMessageView.as_view(), name="view_message"),
    path('roleprofiles/', account.RoleProfileListView.as_view(), name='roleprofile_list'),
]
