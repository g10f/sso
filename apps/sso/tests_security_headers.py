from django.test import TestCase
from django.urls import reverse


class SecurityHeaderTests(TestCase):
    """
    SecurityMiddleware adds the headers the proxy in front of us does not set.
    """
    def test_html_response(self):
        response = self.client.get(reverse('home'))
        self.assertEqual('nosniff', response.headers['X-Content-Type-Options'])
        self.assertEqual('same-origin', response.headers['Referrer-Policy'])

    def test_json_response(self):
        response = self.client.get(reverse('openid-configuration'))
        self.assertTrue(response.headers['Content-Type'].startswith('application/json'))
        self.assertEqual('nosniff', response.headers['X-Content-Type-Options'])
        self.assertEqual('same-origin', response.headers['Referrer-Policy'])

    def test_no_cross_origin_opener_policy(self):
        # would cut window.opener for clients opening the login with display=popup
        response = self.client.get(reverse('auth:login'))
        self.assertNotIn('Cross-Origin-Opener-Policy', response.headers)

    def test_hsts_is_left_to_the_proxy(self):
        response = self.client.get(reverse('home'), secure=True)
        self.assertNotIn('Strict-Transport-Security', response.headers)
