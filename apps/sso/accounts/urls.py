from django.contrib.auth.views import PasswordResetDoneView, PasswordResetCompleteView
from django.urls import path
from django.views.generic import TemplateView
from .views import PasswordResetView, PasswordResetConfirmView, PasswordChangeDoneView, PasswordCreateConfirmView
from .views import application, PasswordCreateCompleteView, usernote
from .views import emails, confirm_email
from .views import onetimemessage
from .views import organisation
from .views import password_change, profile, contact, delete_profile

app_name = 'accounts'

urlpatterns = [
    path('', application.UserList.as_view(), name='user_list'),
    path('me/', profile, name='profile'),
    path('add/', application.add_user, name='add_user'),
    path('add/done/<uuid:uuid>/', application.add_user_done, name="add_user_done"),
    path('<uuid:uuid>/', application.update_user, name="update_user"),
    path('<uuid:uuid>/delete/', application.UserDeleteView.as_view(), name="delete_user"),
    path('<uuid:uuid>/notes/delete/', usernote.UserNoteDeleteView.as_view(), name="delete_user_note"),
    path('app_admin/', application.AppAdminUserList.as_view(), name='app_admin_user_list'),
    path('app_admin/<uuid:uuid>/', application.app_admin_update_user, name="app_admin_update_user"),
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
    path('messages/<uuid:uuid>/', onetimemessage.OneTimeMessageView.as_view(), name="view_message"),
    path('roleprofiles/', application.RoleProfileListView.as_view(), name='roleprofile_list'),
]
