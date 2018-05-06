from django.conf.urls import url
from sso.access_requests.views import AccountExtendAccessView, AccountExtendAccessDoneView

urlpatterns = [
    url(r'^extend_access/$', AccountExtendAccessView.as_view(), name='extend_access'),
    url(r'^extend_access/thanks/$', AccountExtendAccessDoneView.as_view(), name='extend_access_thanks'),
]
