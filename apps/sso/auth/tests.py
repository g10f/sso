from django.core import signing
from django.test import TestCase
from django.urls import reverse

from sso.auth.views import SALT


class TokenViewSignatureTests(TestCase):
    """Regression tests for sso.auth.views.TokenView.dispatch.

    An invalid signed ``user_data`` token must not raise an unhandled
    exception (HTTP 500 + admin email); the user is sent back to the login
    page instead.
    """

    def _token_url(self, user_data, device_id=1):
        return reverse('auth:token', kwargs={'device_id': device_id, 'user_data': user_data})

    def test_tampered_token_redirects_to_login(self):
        # a syntactically plausible but tampered token raises signing.BadSignature
        tampered = ('eyJ1c2VyX2lkIjozLCJiYWNrZW5kIjoic3NvLmF1dGguYmFja2VuZHMuRW1h'
                    'aWxCYWNrZW5kIiwiZXhwaXJ5IjowfQ:1xDQtH:tampered-signature-value')
        response = self.client.get(self._token_url(tampered))
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(response.status_code, 302)

    def test_valid_signature_unknown_user_redirects_to_login(self):
        # a correctly signed token for a user that does not exist raises
        # User.DoesNotExist (ObjectDoesNotExist)
        user_data = signing.dumps(
            {'user_id': 999999, 'backend': 'sso.auth.backends.EmailBackend', 'expiry': 0},
            salt=SALT)
        response = self.client.get(self._token_url(user_data))
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(response.status_code, 302)
