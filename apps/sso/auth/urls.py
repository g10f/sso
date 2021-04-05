from django.urls import path

from sso.auth.views import LoginView, TokenView, logout
from sso.auth.views.profile import DetailView, AddTOTP, AddU2FView

app_name = 'auth'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout, name='logout'),
    path('token/<int:device_id>/<str:user_data>/', TokenView.as_view(), name='token'),
    path('mfa/', DetailView.as_view(), name='mfa-detail'),
    path('totp/add_device/', AddTOTP.as_view(), name='totp_add_device'),
    path('u2f/add_device/', AddU2FView.as_view(), name='u2f_add_device'),
]
