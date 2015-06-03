from django.conf.urls import url
from sso.auth.views import LoginView, TokenView
from sso.auth.views.profile import ProfileView, TOTPSetup, PhoneSetupView, AddPhoneView

urlpatterns = [
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^login/otp/$', LoginView.as_view(is_otp=True), name='login_otp'),
    url(r'^token/(?P<device_id>[\d]+)/(?P<user_data>[^/]+)/$', TokenView.as_view(), name='token'),
    url(r'^profile/$', ProfileView.as_view(), name='profile'),
    url(r'^profile/totp_setup/$', TOTPSetup.as_view(), name='profile_totp_setup'),
    url(r'^profile/add_phone/$', AddPhoneView.as_view(), name='add_phone'),
    url(r'^profile/phone_setup/(?P<sms_device_id>[\d]+)/$', PhoneSetupView.as_view(), name='phone_setup'),
]
