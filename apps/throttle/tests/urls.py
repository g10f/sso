from django.http import HttpResponse
from django.urls import re_path
from throttle.decorators import throttle
from throttle.tests import index

urlpatterns = [
    re_path(r'^$', throttle()(index), name='test_default'),
    re_path(r'^method/$', throttle(method='GET')(index), name='test_method'),
    re_path(r'^duration/$', throttle(duration=0)(index), name='test_duration'),
    re_path(r'^response/$', throttle(response=HttpResponse('Response', status=401))(index), name='test_response'),
    re_path(r'^response/callable/$', throttle(response=lambda request: HttpResponse('Request Response', status=401))(index),
            name='test_response_callable'),
]
