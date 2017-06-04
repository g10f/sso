from django import test
from django.http import HttpResponse
from django.test import override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF='throttle.tests.urls')
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
