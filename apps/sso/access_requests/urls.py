from django.conf.urls import url
from sso.access_requests.views import AccountExtendAccessView, AccountExtendAccessDoneView, AccessRequestList, \
    AccountExtendAccessAcceptView

app_name = 'access_requests'

urlpatterns = [
    url(r'^new/$', AccountExtendAccessView.as_view(), name='extend_access'),
    url(r'^thanks/$', AccountExtendAccessDoneView.as_view(), name='extend_access_thanks'),
    url(r'^$', AccessRequestList.as_view(), name='extend_access_list'),
    url(r'^(?P<pk>\d+)/accept/$', AccountExtendAccessAcceptView.as_view(),
        name='extend_access_accept'),
]
