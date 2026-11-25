import time
from unittest import mock
from urllib.parse import urlencode

from django.core import signing
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from sso.auth.models import U2FDevice
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


class LogoutIdTokenHintTests(TestCase):
    """Regression: an invalid id_token_hint on the logout endpoint must not
    raise an unhandled exception (HTTP 500 + admin email)."""

    def test_invalid_id_token_hint_does_not_error(self):
        response = self.client.get(reverse('auth:logout'), data={
            'post_logout_redirect_uri': 'https://example.com/after-logout',
            'id_token_hint': 'not-a-valid-jwt',
        })
        self.assertNotEqual(response.status_code, 500)


class U2FRegisterCompleteTests(TestCase):
    """Regression: a tampered WebAuthn registration state must raise a clean
    ValidationError instead of signing.BadSignature bubbling up to an HTTP 500.
    AddU2FView.form_valid catches ValidationError and re-renders the form."""

    def test_tampered_state_raises_validation_error(self):
        from django.contrib.auth import get_user_model
        from django.core.exceptions import ValidationError
        user = get_user_model()(username='u2ftest')
        with self.assertRaises(ValidationError):
            U2FDevice.register_complete('dev', '{}', 'tampered-state', user)


class LoginCsrfFailureTests(TestCase):
    """A login form submitted twice: the first POST logs in and rotates the CSRF token, the second
    one carries the old token. sso.auth.views.csrf.csrf_failure sends the logged-in user on instead
    of showing a 403, and keeps the next parameter on the 403 page otherwise."""
    fixtures = ['roles.json', 'test_l10n_data.json', 'test_organisation_data.json', 'app_roles.json',
                'test_app_roles.json', 'test_user_data.json']
    next_url = '/accounts/me/?foo=bar'

    def setUp(self):
        from sso.test.client import SSOClient
        self.client = SSOClient(enforce_csrf_checks=True)
        self.login_url = '%s?%s' % (reverse('auth:login'), urlencode({'next': self.next_url}))

    def post_login(self, token, password='gsf'):
        return self.client.post(self.login_url, {
            'username': 'GunnarScherf', 'password': password, 'csrfmiddlewaretoken': token})

    def test_second_submit_after_login_continues(self):
        self.client.get(self.login_url)
        token = self.client.cookies['csrftoken'].value
        first = self.post_login(token)
        self.assertEqual(first.status_code, 302)
        self.assertNotEqual(self.client.cookies['csrftoken'].value, token)  # rotated by the login

        second = self.post_login(token)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second['Location'], first['Location'])

    def test_failed_csrf_check_without_login_keeps_next(self):
        self.client.get(self.login_url)
        response = self.post_login('x' * 32)
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'CSRF verification failed', status_code=403)
        self.assertContains(response, 'href="%s"' % escape(self.login_url), status_code=403)

    def test_missing_cookie_is_explained(self):
        response = self.post_login('x' * 32)
        self.assertContains(response, 'requires a CSRF cookie', status_code=403)

    def test_logged_in_user_gets_403_outside_the_login(self):
        self.client.get(self.login_url)
        self.post_login(self.client.cookies['csrftoken'].value)
        response = self.client.post(reverse('accounts:profile'), {'csrfmiddlewaretoken': 'x' * 32})
        self.assertEqual(response.status_code, 403)

    def test_stale_login_form_of_an_older_session_gets_403(self):
        # e.g. a login form requested with prompt=login must not be skipped by an old session
        from sso.auth.views.csrf import DOUBLE_SUBMIT_MAX_SECONDS
        self.client.get(self.login_url)
        token = self.client.cookies['csrftoken'].value
        self.post_login(token)
        later = time.time() + DOUBLE_SUBMIT_MAX_SECONDS + 1
        with mock.patch('sso.auth.views.csrf.time.time', return_value=later):
            response = self.post_login(token)
        self.assertEqual(response.status_code, 403)

    def test_login_form_is_submitted_once(self):
        response = self.client.get(self.login_url)
        self.assertContains(response, 'data-single-submit')
        self.assertContains(response, 'single_submit')
