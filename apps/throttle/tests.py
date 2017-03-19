from django import test
from django.conf.urls import url
from django.http import HttpResponse
from django.urls import reverse
from .decorators import throttle


class ThrottleTest(test.TestCase):
    """
    Throttle decorator test suite
    """
    urls = 'throttle.tests'

    def request(self, url, method='post', **kwargs):
        """
        The helper function that emulates HTTP request to 
        Django views with given method
        """
        url = reverse(url)
        method = method.lower()
        return getattr(test.Client(), method)(url, **kwargs)

    def test_default(self):
        """
        Tests default usage
        """
        self.assertEquals(200, self.request('test_default').status_code)
        self.assertEquals(403, self.request('test_default').status_code)

    def test_method(self):
        """
        Tests that decorator applies to view for specified method and
        not applies for another
        """
        self.assertEquals(200, self.request('test_method', method='GET').status_code)
        self.assertEquals(403, self.request('test_method', method='GET').status_code)
        self.assertEquals(200, self.request('test_method', method='POST').status_code)

    def test_response(self):
        """
        Tests custom response decorator argument
        """
        self.assertEquals(200, self.request('test_response').status_code)
        self.assertEquals(401, self.request('test_response').status_code)
        self.assertEquals(True, 'Response' in self.request('test_response').content)

    def test_response_callable(self):
        """
        Tests custom response decorator argument
        """
        self.assertEquals(200, self.request('test_response_callable').status_code)
        self.assertEquals(401, self.request('test_response_callable').status_code)
        self.assertEquals(True, 'Request Response' in self.request('test_response_callable').content)

    def test_duration(self):
        """
        Tests custom duration
        """
        self.assertEquals(200, self.request('test_duration').status_code)
        self.assertEquals(200, self.request('test_duration').status_code)

def index(request):
    """
    Test view function
    """
    return HttpResponse("Test view")

urlpatterns = [
    url(r'^$', throttle()(index), name='test_default'),
    url(r'^method/$', throttle(method='GET')(index), name='test_method'),
    url(r'^duration/$', throttle(duration=0)(index), name='test_duration'),
    url(r'^response/$', throttle(response=HttpResponse('Response', status=401))(index), name='test_response'),
    url(r'^response/callable/$', throttle(response=lambda request: HttpResponse('Request Response', status=401))(index), name='test_response_callable'),
]
