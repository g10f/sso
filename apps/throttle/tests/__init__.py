from django import test
from django.core.cache import cache
from django.http import HttpResponse
from django.test import override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF='throttle.tests.urls')
class ThrottleTest(test.TestCase):
    """
    Throttle decorator test suite
    """
    urls = 'throttle.tests'

    def setUp(self):
        # the throttle counters live in the cache; isolate the tests
        cache.clear()

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
        self.assertEqual(200, self.request('test_default').status_code)
        self.assertEqual(403, self.request('test_default').status_code)

    def test_method(self):
        """
        Tests that decorator applies to view for specified method and
        not applies for another
        """
        self.assertEqual(200, self.request('test_method', method='GET').status_code)
        self.assertEqual(403, self.request('test_method', method='GET').status_code)
        self.assertEqual(200, self.request('test_method', method='POST').status_code)

    def test_response(self):
        """
        Tests custom response decorator argument
        """
        self.assertEqual(200, self.request('test_response').status_code)
        self.assertEqual(401, self.request('test_response').status_code)
        self.assertEqual(True, b'Response' in self.request('test_response').content)

    def test_response_callable(self):
        """
        Tests custom response decorator argument
        """
        self.assertEqual(200, self.request('test_response_callable').status_code)
        self.assertEqual(401, self.request('test_response_callable').status_code)
        self.assertEqual(True, b'Request Response' in self.request('test_response_callable').content)

    def test_duration(self):
        """
        Tests custom duration
        """
        self.assertEqual(200, self.request('test_duration').status_code)
        self.assertEqual(200, self.request('test_duration').status_code)

    def test_query_string_does_not_bypass(self):
        """
        A different query string must not reset the throttle counter; the key
        is based on the path only.
        """
        url = reverse('test_default')
        self.assertEqual(200, test.Client().post(url + '?x=1').status_code)
        self.assertEqual(403, test.Client().post(url + '?x=2').status_code)

    def test_key_fields_separate_accounts(self):
        """
        With key_fields, different accounts (same IP) get their own counter, so
        users behind a shared IP do not throttle each other; case/whitespace
        variants of the same account still share the counter.
        """
        url = reverse('test_key_fields')
        c = test.Client()
        self.assertEqual(200, c.post(url, {'username': 'alice'}).status_code)
        self.assertEqual(403, c.post(url, {'username': 'alice'}).status_code)
        # different account from the same client is not affected
        self.assertEqual(200, c.post(url, {'username': 'bob'}).status_code)
        # case/whitespace variation must not reset alice's counter
        self.assertEqual(403, c.post(url, {'username': '  ALICE '}).status_code)


def index(request):
    """
    Test view function
    """
    return HttpResponse("Test view")
