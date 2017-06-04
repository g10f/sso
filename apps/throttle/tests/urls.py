from django.conf.urls import url
from django.http import HttpResponse
from throttle.decorators import throttle
from throttle.tests import index

urlpatterns = [
    url(r'^$', throttle()(index), name='test_default'),
    url(r'^method/$', throttle(method='GET')(index), name='test_method'),
    url(r'^duration/$', throttle(duration=0)(index), name='test_duration'),
    url(r'^response/$', throttle(response=HttpResponse('Response', status=401))(index), name='test_response'),
    url(r'^response/callable/$', throttle(response=lambda request: HttpResponse('Request Response', status=401))(index),
        name='test_response_callable'),
]
