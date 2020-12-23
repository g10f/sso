from django.urls import path
from sso.access_requests.views import AccountExtendAccessView, AccountExtendAccessDoneView, AccessRequestList, \
    AccountExtendAccessAcceptView, AccessRequestSendMailFormView

app_name = 'access_requests'

urlpatterns = [
    path('', AccessRequestList.as_view(), name='extend_access_list'),
    path('new/', AccountExtendAccessView.as_view(), name='extend_access'),
    path('thanks/', AccountExtendAccessDoneView.as_view(), name='extend_access_thanks'),
    path('<int:pk>/accept/', AccountExtendAccessAcceptView.as_view(), name='extend_access_accept'),
    path('process/<int:pk>/<slug:action>/', AccessRequestSendMailFormView.as_view(), name="process_access_request"),
]
