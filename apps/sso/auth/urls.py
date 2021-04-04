from django.urls import path

from sso.auth.views import LoginView, TokenView, logout
from sso.auth.views.profile import ProfileView, TOTPSetup, AddU2FView

app_name = 'auth'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout, name='logout'),
    path('token/<int:device_id>/<str:user_data>/', TokenView.as_view(), name='token'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/totp_setup/', TOTPSetup.as_view(), name='profile_totp_setup'),
    path('profile/u2f/add_device/', AddU2FView.as_view(), name='u2f_add_device'),
]
