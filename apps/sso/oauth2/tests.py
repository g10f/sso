import base64
import hashlib
import json
import logging
import re
import uuid
from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from time import sleep
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.forms import modelform_factory
from django.http import QueryDict, SimpleCookie
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from sso.accounts.forms import ClientForm
from sso.auth.models import Device
from sso.test.client import SSOClient
from . import crypt
from .admin import ClientAdminForm
from .models import Client, RefreshToken, AuthorizationCode, DeviceCode


def get_query_dict(url):
    scheme, netloc, path, query_string, fragment = urlsplit(url)  # @UnusedVariable
    query_dict = QueryDict(query_string).copy()
    return query_dict


def get_fragment_dict(url):
    scheme, netloc, path, query_string, fragment = urlsplit(url)  # @UnusedVariable
    fragment_dict = QueryDict(fragment).copy()
    return fragment_dict


class OAuth2BaseTestCase(TestCase):
    fixtures = ['roles.json', 'test_l10n_data.json', 'test_organisation_data.json', 'app_roles.json',
                'test_app_roles.json', 'test_user_data.json', 'test_oauth2_data.json']
    _client_id = "ec1e39cbe3e746c787b770ace4165d13"
    _state = 'eyJub25jZSI6Ik1sSllaUlc3VWdGdyIsInByb3ZpZGVyIjoyLCJuZXh0IjoiLyJ9'

    def setUp(self):
        # signing keys are cached, but the keys in the database are rolled back after each test
        cache.clear()
        self.client = SSOClient()

    def logout(self):
        self.client.logout()
        self.client.cookies = SimpleCookie()

    def login_and_get_code(self, client_id=None, max_age=None, wait=0, username='GunnarScherf', password='gsf',
                           scope="openid profile email", code_challenge=None, code_challenge_method=None,
                           should_succeed=True):
        self.client.login(username=username, password=password)
        if wait > 0:
            sleep(wait)

        authorize_data = {
            'scope': scope,
            'state': self._state,
            'redirect_uri': "http://localhost",
            'response_type': "code",
            'client_id': client_id if client_id else self._client_id,
        }
        if max_age:
            authorize_data['max_age'] = max_age
        if code_challenge:
            authorize_data['code_challenge'] = code_challenge
        if code_challenge_method:
            authorize_data['code_challenge_method'] = code_challenge_method

        response = self.client.get(reverse('oauth2:authorize'), data=authorize_data)
        self.assertEqual(response.status_code, 302)
        query_dict = get_query_dict(response['Location'])
        self.assertTrue(set({'state': self._state}.items()).issubset(set(query_dict.items())))
        if should_succeed:
            self.assertIn('code', query_dict)
            return query_dict['code']
        return query_dict

    def login_and_get_implicit_id_token(self, client_id='92d7d9d71d5d41caa652080c19aaa6d8', max_age=None, wait=0,
                                        username='GunnarScherf', password='gsf', response_type="id_token token"):
        self.client.login(username=username, password=password)
        if wait > 0:
            sleep(wait)

        authorize_data = {
            'scope': "openid profile email",
            'state': self._state,
            'nonce': get_random_string(12),
            'redirect_uri': "http://localhost",
            'response_type': response_type,
            'client_id': client_id,
        }
        if max_age:
            authorize_data['max_age'] = max_age

        response = self.client.get(reverse('oauth2:authorize'), data=authorize_data)
        self.assertEqual(response.status_code, 302)
        fragment_dict = get_fragment_dict(response['Location'])

        self.assertIn('id_token', fragment_dict)
        expected = {'state': self._state}
        self.assertTrue(set(expected.items()).issubset(set(fragment_dict.items())))
        return fragment_dict

    def get_authorization(self, client_id=None, username='GunnarScherf', password='gsf', scope="openid profile email"):
        code = self.login_and_get_code(client_id, username=username, password=password, scope=scope)
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id if client_id else self._client_id,
            'code': code
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('application/json', token_response['Content-Type'])
        token = token_response.json()
        self.logout()
        return 'Bearer %s' % token['access_token']

    def get_authorization_with_client_credentials(self, client_id=None, client_secret='geheim', scope="openid profile email"):
        token_response = self.token_request_with_client_credentials(client_id, client_secret=client_secret, scope=scope)
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('application/json', token_response['Content-Type'])
        token = token_response.json()
        self.logout()
        return 'Bearer %s' % token['access_token']

    def get_http_authorization(self, data):
        if 'client_secret' in data and data['client_secret']:
            auth = b"%s:%s" % (data['client_id'].encode(), data['client_secret'].encode())
            del data['client_id']
            del data['client_secret']
            return '%s %s' % ('Basic', base64.b64encode(auth).decode("ascii"))
        else:
            return None

    def token_request(self, token_data):
        data = token_data.copy()
        authorization = self.get_http_authorization(data)
        return self.client.post(reverse('oauth2:token'), data, HTTP_AUTHORIZATION=authorization)

    def token_request_with_client_credentials(self, client_id=None, client_secret="geheim", scope="openid profile email"):
        data = {
            'grant_type': "client_credentials",
            'client_secret': client_secret,
            'client_id': client_id if client_id else self._client_id,
        }
        if scope:
            data['scope'] = scope
        return self.client.post(reverse('oauth2:token'), data)

    def get_url_from_mail(self, n=1):
        outbox = getattr(mail, 'outbox')
        self.assertTrue(len(outbox) >= n)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+',
                          outbox[n-1].body)
        self.assertEqual(len(urls), 1)
        return urls[0]


class OAuth2Tests(OAuth2BaseTestCase):
    def test_login_and_get_code_failure(self):
        self.client.login(username='GunnarScherf', password='gsf')
        authorize_data = {
            'scope': "openid profile email",
            'state': self._state,
            'redirect_uri': "http://error_domain",
            'response_type': "code",
            'client_id': self._client_id
        }

        response = self.client.get(reverse('oauth2:authorize'), data=authorize_data)
        self.assertEqual(response.status_code, 302)
        query_dict = get_query_dict(response['Location'])

        self.assertIn('error', query_dict)
        expected = {'error': 'invalid_request'}
        self.assertTrue(set(expected.items()).issubset(set(query_dict.items())))

        self.assertEqual(urlsplit(response['Location'])[2], reverse('oauth2:oauth2_error'))

        response = self.client.get(response['Location'])
        self.assertEqual(response.context['error'], 'invalid_request')

    def test_login_and_get_code_max_age_failure(self):
        self.client.login(username='GunnarScherf', password='gsf')
        max_age = 2
        sleep(max_age + 1)
        authorize_data = {
            'scope': "openid profile email",
            'state': self._state,
            'redirect_uri': "http://localhost",
            'response_type': "code",
            'client_id': self._client_id,
            'max_age': max_age
        }

        response = self.client.get(reverse('oauth2:authorize'), data=authorize_data)
        # check if the response is a redirect to the login page
        self.assertEqual(response.status_code, 302)
        path = urlsplit(response['Location'])[2]
        self.assertEqual(path, reverse('auth:login'))

    def test_get_implicit_id_token_and_access_token(self):
        """
        implicit login with access_token and id_token
        """
        fragment_dict = self.login_and_get_implicit_id_token()
        self.assertIn('access_token', fragment_dict)
        self.assertEqual(fragment_dict['expires_in'], str(settings.SSO_ACCESS_TOKEN_AGE))
        self.assertEqual(fragment_dict['token_type'], 'Bearer')
        self.assertEqual(fragment_dict['scope'], 'openid profile email')
        self.assertEqual(fragment_dict['state'], self._state)

    def test_get_implicit_id_token(self):
        """
        implicit login with id_token only
        """
        fragment_dict = self.login_and_get_implicit_id_token(response_type="id_token")
        self.assertNotIn('access_token', fragment_dict)
        self.assertEqual(fragment_dict['state'], self._state)

    def test_get_token_scopes(self):
        code = self.login_and_get_code(scope="openid profile email test")
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': self._client_id,
            'code': code,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()
        expected = {'scope': 'openid profile email test', 'token_type': 'Bearer'}
        self.assertTrue(set(expected.items()).issubset(set(token.items())))

        with self.assertRaises(AssertionError) as cm:
            self.login_and_get_code(scope="openid profile email test2")
        self.assertIn("invalid_scope", str(cm.exception))

    def test_get_token(self):
        code = self.login_and_get_code()
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': self._client_id,
            'code': code,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('application/json', token_response['Content-Type'])
        self.assertEqual(token_response['Cache-Control'], 'no-store')
        self.assertEqual(token_response['Pragma'], 'no-cache')

        token = token_response.json()
        self.assertIn('access_token', token)
        self.assertIn('id_token', token)
        self.assertIn('expires_in', token)
        self.assertIn('scope', token)
        self.assertIn('token_type', token)

        expected = {'scope': 'openid profile email', 'token_type': 'Bearer'}
        self.assertTrue(set(expected.items()).issubset(set(token.items())))

        id_token = crypt.loads_jwt(token['id_token'])
        self.assertIn('iss', id_token)
        self.assertIn('sub', id_token)
        self.assertIn('aud', id_token)
        self.assertIn('exp', id_token)
        self.assertIn('iat', id_token)
        self.assertIn('email', id_token)
        self.assertIn('name', id_token)
        self.assertIn('roles', id_token)

        expected = {
            'iss': 'http://testserver',
            'sub': 'a8992f0348634f76b0dac2de4e4c83ee',  # user_id
            'aud': self._client_id,
            'email': 'gunnar@g10f.de',
            'name': 'GunnarScherf'
        }
        self.assertTrue(set(expected.items()).issubset(set(id_token.items())))

        roles = id_token['roles'].split()
        self.assertIn('Admin', roles)
        self.assertIn('Staff', roles)

        authorization = 'Bearer %s' % token['access_token']
        self.logout()

        response = self.client.get(reverse('openid-configuration'))
        configuration = response.json()

        # no authentication
        response = self.client.get(configuration['userinfo_endpoint'])
        self.assertEqual(response.status_code, 401)

        # valid authentication
        response = self.client.get(configuration['userinfo_endpoint'], HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        user_info = response.json()
        self.assertEqual(user_info['family_name'], 'Scherf')
        # organisations are no standard claim, they are available in the v2 users api
        self.assertNotIn('organisations', user_info)
        response = self.client.get(reverse('api:v2_users_me'), HTTP_AUTHORIZATION=authorization)
        self.assertIn('31664dd38ca4454e916e55fe8b1f0745', response.json()['organisations'])

        # this is only for global admin accounts
        response = self.client.get(reverse('api:v1_users'), HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 401)

    def test_refresh_token(self):
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email offline_access')
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('application/json', token_response['Content-Type'])
        self.assertEqual(token_response['Cache-Control'], 'no-store')
        self.assertEqual(token_response['Pragma'], 'no-cache')

        token = token_response.json()
        self.assertIn('access_token', token)
        self.assertIn('id_token', token)
        self.assertIn('refresh_token', token)
        self.assertIn('expires_in', token)
        self.assertIn('scope', token)
        self.assertIn('token_type', token)

        self.assertTrue({'scope': 'openid profile email offline_access', 'token_type': 'Bearer'}, token)

        id_token = crypt.loads_jwt(token['id_token'])
        self.assertIn('iss', id_token)
        self.assertIn('sub', id_token)
        self.assertIn('aud', id_token)
        self.assertIn('exp', id_token)
        self.assertIn('iat', id_token)
        self.assertIn('email', id_token)
        self.assertIn('name', id_token)
        self.assertIn('roles', id_token)

        expected = {
            'iss': 'http://testserver',
            'sub': 'a8992f0348634f76b0dac2de4e4c83ee',  # user_id
            'aud': client_id,
            'email': 'gunnar@g10f.de',
            'name': 'GunnarScherf'
        }
        self.assertTrue(set(expected.items()).issubset(set(id_token.items())))

        roles = id_token['roles'].split()
        self.assertIn('Admin', roles)
        self.assertIn('Staff', roles)

        authorization = 'Bearer %s' % token['access_token']
        self.logout()

        response = self.client.get(reverse('openid-configuration'))
        configuration = response.json()

        # no authentication
        response = self.client.get(configuration['userinfo_endpoint'])
        self.assertEqual(response.status_code, 401)

        # valid authentication
        response = self.client.get(configuration['userinfo_endpoint'], HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        user_info = response.json()
        self.assertEqual(user_info['family_name'], 'Scherf')
        # organisations are no standard claim, they are available in the v2 users api
        self.assertNotIn('organisations', user_info)
        response = self.client.get(reverse('api:v2_users_me'), HTTP_AUTHORIZATION=authorization)
        self.assertIn('31664dd38ca4454e916e55fe8b1f0745', response.json()['organisations'])

        # this is only for global admin accounts
        response = self.client.get(reverse('api:v1_users'), HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 401)

        # get a new access_token from the refresh_token
        token_data = {
            'grant_type': "refresh_token",
            'refresh_token': token['refresh_token'],
            'client_id': client_id,
            'client_secret': "geheim",
        }
        sleep(1)  # wait 1 sec, so that iat of the new id_token is different
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertIn('application/json', token_response['Content-Type'])
        self.assertEqual(token_response['Cache-Control'], 'no-store')
        self.assertEqual(token_response['Pragma'], 'no-cache')

        token = token_response.json()
        self.assertIn('access_token', token)
        if 'id_token' in token:
            # check the id_token from refresh token response
            # https://openid.net/specs/openid-connect-core-1_0.html#RefreshTokenResponse
            id_token_from_refresh = crypt.loads_jwt(token['id_token'])
            self.assertEqual(id_token_from_refresh['iss'], id_token['iss'])
            self.assertEqual(id_token_from_refresh['sub'], id_token['sub'])
            self.assertNotEqual(id_token_from_refresh['iat'], id_token['iat'])
            self.assertEqual(id_token_from_refresh['aud'], id_token['aud'])
            if 'auth_time' in id_token:
                self.assertEqual(id_token_from_refresh['auth_time'], id_token['auth_time'])
            if 'azp' in id_token:
                self.assertEqual(id_token_from_refresh['azp'], id_token['azp'])

        # self.assertNotIn('id_token', token)
        self.assertIn('refresh_token', token)
        self.assertIn('expires_in', token)
        self.assertIn('scope', token)
        self.assertIn('token_type', token)

        self.assertTrue({'scope': 'openid profile email', 'token_type': 'Bearer'}, token)

        # test that refresh tokens can only be used once
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)
        self.assertIn('error', token_response.json())

        # revoke the last refresh token
        data = {
            'token': token['refresh_token'],
            'client_id': client_id,
            'client_secret': "geheim",
        }
        revoke_response = self.client.post(reverse('oauth2:revoke'), data)
        self.assertEqual(revoke_response.status_code, 200)

        # using the last refresh token should fail (revoked)
        token_data = {
            'grant_type': "refresh_token",
            'refresh_token': token['refresh_token'],
            'client_id': client_id,
            'client_secret': "geheim",
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)
        token = token_response.json()
        self.assertIn('error', token)

    def test_revoke_refresh_token(self):
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email offline_access')

        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()

        authorization = self.get_http_authorization(token_data)

        data = {'token': token['refresh_token']}
        response = self.client.post(reverse('oauth2:introspect'), data, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(True, response.json()['active'])

        data = {'token': token['access_token']}
        response = self.client.post(reverse('oauth2:introspect'), data, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(True, response.json()['active'])

        data = {'token': token['refresh_token']}
        response = self.client.post(reverse('oauth2:revoke'), data, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('oauth2:introspect'), data, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(False, response.json()['active'])

    def test_pkce(self):
        # test client with optional pkce
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        code_verifier = get_random_string(12)
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=')
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email',
                                       code_challenge=code_challenge, code_challenge_method='S256')

        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
            'code_verifier': code_verifier,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        # test client with optional pkce and wrong code_verifier
        code_verifier = get_random_string(12)
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=')
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email',
                                       code_challenge=code_challenge, code_challenge_method='S256')

        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
            'code_verifier': 'wrong_code_verifier',
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)

        # test client with pkce required
        client_id = 'ec4c46551416431db114a4c54d552f5b'
        code_verifier = get_random_string(12)
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=')
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email',
                                       code_challenge=code_challenge, code_challenge_method='S256')

        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
            'code_verifier': code_verifier,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)

        # test client with pkce required not sending pkce data
        query_dict = self.login_and_get_code(client_id=client_id, scope='openid profile email', should_succeed=False)
        self.assertIn('error', query_dict)
        self.assertEqual('invalid_request', query_dict['error'])
        self.assertEqual('Code challenge required.', query_dict['error_description'])

    def test_pkce_non_ascii_code_verifier(self):
        # Regression: oauthlib 4 compares with hmac.compare_digest, which raises TypeError for non-ASCII
        # strings. A malformed code_verifier must be rejected with 400, not end in a 500.
        # (with S256 the verifier is hashed first, so only the plain method is affected)
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        code = self.login_and_get_code(client_id=client_id, scope='openid profile email',
                                       code_challenge=get_random_string(43), code_challenge_method='plain')
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id,
            'code': code,
            'code_verifier': 'ä' * 43,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)

    @override_settings(SSO_DEVICE_AUTHORIZATION_GRANT=False)
    def test_discovery_grant_types_supported(self):
        response = self.client.get(reverse('openid-configuration'))
        self.assertEqual(response.json()['grant_types_supported'],
                         ['authorization_code', 'implicit', 'refresh_token', 'client_credentials', 'password'])

    def test_get_token_with_dashed_client_id(self):
        # Regression: oauthlib 4 raises server_error if request.client_id differs from client.client_id
        # (uuid.hex), but clients may send the client_id in the dashed UUID format.
        code = self.login_and_get_code()
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': str(uuid.UUID(self._client_id)),
            'code': code
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        # clients compare the aud claim of the id_token with their client_id as configured
        id_token = crypt.loads_jwt(token_response.json()['id_token'])
        self.assertEqual(id_token['aud'], str(uuid.UUID(self._client_id)))

    def test_client_id_format_is_recorded(self):
        client = Client.objects.get(uuid=self._client_id)
        self.assertEqual(client.client_id_format, '')
        last_modified = client.last_modified
        for client_id, client_id_format in ((str(uuid.UUID(self._client_id)), 'dashed'),
                                            (self._client_id.upper(), 'other'),
                                            (self._client_id, 'hex')):
            self.login_and_get_code(client_id=client_id)
            client.refresh_from_db()
            self.assertEqual(client.client_id_format, client_id_format)
            self.logout()
        self.assertEqual(client.last_modified, last_modified)

    def test_public_client_with_dashed_client_id(self):
        # e.g. kubelogin: a public client without client secret, configured with the dashed client_id
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        Client.objects.filter(uuid=client_id).update(type='native', client_secret='')
        dashed_client_id = str(uuid.UUID(client_id))
        code = self.login_and_get_code(client_id=dashed_client_id)
        data = {'grant_type': "authorization_code", 'redirect_uri': "http://localhost", 'client_id': dashed_client_id,
                'code': code}
        token_response = self.client.post(reverse('oauth2:token'), data)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(crypt.loads_jwt(token_response.json()['id_token'])['aud'], dashed_client_id)

    def test_refresh_token_with_dashed_client_id(self):
        client_id = '5614cdb0aa3c48d59828681bd62e1741'
        dashed_client_id = str(uuid.UUID(client_id))
        code = self.login_and_get_code(client_id=dashed_client_id, scope='openid profile email offline_access')
        data = {'grant_type': "authorization_code", 'redirect_uri': "http://localhost", 'client_secret': "geheim",
                'client_id': dashed_client_id, 'code': code}
        token = self.client.post(reverse('oauth2:token'), data).json()  # client_secret_post
        self.assertEqual(crypt.loads_jwt(token['id_token'])['aud'], dashed_client_id)

        data = {'grant_type': "refresh_token", 'client_secret': "geheim", 'client_id': dashed_client_id,
                'refresh_token': token['refresh_token']}
        token_response = self.client.post(reverse('oauth2:token'), data)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(crypt.loads_jwt(token_response.json()['id_token'])['aud'], dashed_client_id)

    def test_get_token_failure(self):
        code = self.login_and_get_code()
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://error_domain",
            'client_secret': "geheim",
            'client_id': self._client_id,
            'code': code
        }

        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)
        # self.assertEqual(token_response.status_code, 401)
        self.assertIn('application/json', token_response['Content-Type'])

        token = token_response.json()
        self.assertIn('error', token)
        # expected = {'error': 'access_denied'}
        expected = {'error': 'invalid_request'}
        self.assertTrue(set(expected.items()).issubset(set(token.items())))

        token_data['redirect_uri'] = "http://localhost"
        token_data['code'] = "wrong_code"

        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 400)
        self.assertIn('application/json', token_response['Content-Type'])

        token = token_response.json()
        self.assertIn('error', token)
        expected = {'error': 'invalid_grant'}
        self.assertTrue(set(expected.items()).issubset(set(token.items())))

    def test_client_credentials_missing_user_logs_warning_not_error(self):
        # Regression: a client_credentials client without an associated user is a
        # client misconfiguration. It must fail authentication and be logged at
        # WARNING (not ERROR, which would trigger an admin email per request).
        # The default "Test Client" (self._client_id) has no user bound.
        logger_name = 'sso.oauth2.oidc_request_validator'
        with self.assertLogs(logger_name, level='WARNING') as cm:
            token_response = self.token_request_with_client_credentials(scope="openid")
        self.assertNotEqual(token_response.status_code, 200)
        self.assertIn('error', token_response.json())
        # the "missing user" message is present and none of the records is ERROR+
        missing = [r for r in cm.records if 'missing user for client' in r.getMessage()]
        self.assertTrue(missing)
        self.assertTrue(all(r.levelno < logging.ERROR for r in missing))

    def test_get_original_scopes_unknown_refresh_token_logs_warning(self):
        # Regression: an unknown/invalid refresh token is client input, not a
        # server fault. get_original_scopes must return [] and log at WARNING
        # (not ERROR, which would send an admin email).
        from sso.oauth2.oidc_request_validator import OIDCRequestValidator
        logger_name = 'sso.oauth2.oidc_request_validator'
        validator = OIDCRequestValidator()
        with self.assertLogs(logger_name, level='WARNING') as cm:
            scopes = validator.get_original_scopes('does-not-exist', None)
        self.assertEqual(scopes, [])
        recs = [r for r in cm.records if 'confirm_scopes' in r.getMessage()]
        self.assertTrue(recs)
        self.assertTrue(all(r.levelno < logging.ERROR for r in recs))

    def test_token_unknown_client_no_server_error(self):
        # Regression: a syntactically valid but unknown client_id must return a
        # proper OAuth2 error response, not raise Client.DoesNotExist -> HTTP 500
        # (which also triggered an admin email per request). See _get_client.
        token_data = {
            'grant_type': "password",
            'client_id': "00000000000000000000000000000000",
            'username': "never-bound@nonexistent.invalid",
            'password': "x",
        }
        token_response = self.token_request(token_data)
        self.assertNotEqual(token_response.status_code, 500)
        self.assertEqual(token_response.status_code, 401)
        self.assertIn('application/json', token_response['Content-Type'])
        self.assertEqual(token_response.json()['error'], 'invalid_client')

    def test_session_init_foreign_origin_returns_404(self):
        # Regression: session_init returned (instead of raised) Http404, which
        # crashed LocaleMiddleware with AttributeError -> HTTP 500 + admin email.
        url = reverse('oauth2:session_init')
        client = Client.objects.get(uuid=self._client_id)
        origin = client.redirect_uris.split()[0]
        response = self.client.get(url, {'client_id': self._client_id, 'origin': origin})
        self.assertEqual(response.status_code, 204)

        for params in [{'client_id': self._client_id, 'origin': 'https://evil.example'},
                       {'client_id': self._client_id},
                       {'client_id': 'not-a-uuid', 'origin': origin},
                       {}]:
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 404, params)


class RefreshTokenBindingTests(OAuth2BaseTestCase):
    client_id = '5614cdb0aa3c48d59828681bd62e1741'
    other_client_id = 'ec4c46551416431db114a4c54d552f5b'  # another confidential client with offline_access

    def get_token(self):
        code = self.login_and_get_code(client_id=self.client_id, scope='openid profile email offline_access')
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': self.client_id,
            'code': code,
        }
        token_response = self.token_request(token_data)
        self.assertEqual(token_response.status_code, 200)
        self.logout()
        return token_response.json()

    def refresh_request(self, refresh_token, client_id, client_secret="geheim"):
        token_data = {
            'grant_type': "refresh_token",
            'refresh_token': refresh_token,
            'client_id': client_id,
        }
        if client_secret:
            token_data['client_secret'] = client_secret
        return self.token_request(token_data)

    def test_refresh_token_of_other_confidential_client(self):
        token = self.get_token()
        response = self.refresh_request(token['refresh_token'], self.other_client_id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

        # the token is not consumed by the failed request and still valid for the own client
        response = self.refresh_request(token['refresh_token'], self.client_id)
        self.assertEqual(response.status_code, 200)

    def test_refresh_token_of_other_public_client(self):
        token = self.get_token()
        # public clients do not authenticate with a secret
        native_client = Client.objects.get(uuid=self.other_client_id)
        native_client.pk = None
        native_client.uuid = uuid.uuid4()
        native_client.type = 'native'
        native_client.save()

        response = self.refresh_request(token['refresh_token'], native_client.uuid.hex, client_secret=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

    def test_expired_refresh_token(self):
        token = self.get_token()
        created_at = timezone.now() - timedelta(seconds=settings.SSO_REFRESH_TOKEN_AGE + 1)
        RefreshToken.objects.filter(token=token['refresh_token']).update(created_at=created_at)

        response = self.refresh_request(token['refresh_token'], self.client_id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')

    def test_revoke_refresh_token_of_other_client(self):
        token = self.get_token()
        data = {'token': token['refresh_token'], 'client_id': self.other_client_id, 'client_secret': "geheim"}
        response = self.client.post(reverse('oauth2:revoke'), data)
        self.assertEqual(response.status_code, 200)  # RFC 7009: invalid tokens are answered with 200 too
        self.assertTrue(RefreshToken.objects.get(token=token['refresh_token']).is_active)

    def test_expired_authorization_code(self):
        code = self.login_and_get_code(client_id=self.client_id, scope='openid profile email offline_access')
        self.logout()
        created_at = timezone.now() - timedelta(seconds=settings.SSO_AUTHORIZATION_CODE_AGE + 1)
        AuthorizationCode.objects.filter(code=code).update(created_at=created_at)

        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': self.client_id,
            'code': code,
        }
        response = self.token_request(token_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_grant')


class AuthorizeOpenRedirectTests(OAuth2BaseTestCase):
    """
    TwoFactorRequiredError is raised before oauthlib has validated the request,
    so the error must not be reported to an arbitrary redirect_uri.
    """
    _acr_claims = json.dumps({'id_token': {'acr': {'values': ['2']}}})

    def authorize(self, redirect_uri):
        self.client.login(username='GunnarScherf', password='gsf')
        authorize_data = {
            'scope': "openid profile email",
            'state': self._state,
            'redirect_uri': redirect_uri,
            'response_type': "code",
            'client_id': self._client_id,
            'claims': self._acr_claims,
        }
        return self.client.get(reverse('oauth2:authorize'), data=authorize_data)

    def test_two_factor_required_no_open_redirect(self):
        # the user has no confirmed 2 factor device, which raises TwoFactorRequiredError
        self.assertFalse(get_user_model().objects.get(username='GunnarScherf').device_set.filter(confirmed=True).exists())

        response = self.authorize("https://evil.example/steal")
        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertNotIn('evil.example', location)
        self.assertEqual(urlsplit(location)[2], reverse('oauth2:oauth2_error'))
        self.assertEqual(get_query_dict(location)['error'], 'two_factor_required')

    def test_two_factor_required_registered_redirect_uri(self):
        # a registered redirect_uri still gets the error reported back
        response = self.authorize("http://localhost")
        self.assertEqual(response.status_code, 302)
        location = response['Location']
        self.assertTrue(location.startswith("http://localhost"))
        query_dict = get_query_dict(location)
        self.assertEqual(query_dict['error'], 'two_factor_required')
        self.assertEqual(query_dict['state'], self._state)


@override_settings(SSO_DEVICE_AUTHORIZATION_GRANT=True)
class DeviceCodeGrantTests(OAuth2BaseTestCase):
    # the 'Test Client - TV (device flow)' fixture: type=native, no client_secret
    _tv_client_id = "3f6a9b6b1a8940e6a3f0a2f7f3f2e1a1"

    def device_authorization_request(self, client_id=None, scope="openid profile email"):
        # RFC 8628's device_authorization endpoint requires application/x-www-form-urlencoded,
        # unlike token/ -- Django's test client defaults to multipart, so this needs encoding explicitly.
        data = {'client_id': client_id if client_id else self._tv_client_id}
        if scope is not None:
            data['scope'] = scope
        return self.client.post(reverse('oauth2:device_authorization'), data=urlencode(data),
                                content_type='application/x-www-form-urlencoded')

    def poll_token(self, device_code, client_id=None):
        return self.client.post(reverse('oauth2:token'), {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'client_id': client_id if client_id else self._tv_client_id,
            'device_code': device_code,
        })

    def test_device_authorization_returns_user_code(self):
        response = self.device_authorization_request()
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
        data = response.json()
        self.assertIn('device_code', data)
        self.assertIn('user_code', data)
        self.assertIn('verification_uri', data)
        self.assertIn('expires_in', data)
        self.assertIn('interval', data)

        device_code_obj = DeviceCode.objects.get(device_code=data['device_code'])
        self.assertEqual(device_code_obj.user_code, data['user_code'])
        self.assertEqual(device_code_obj.status, DeviceCode.STATUS_PENDING)
        self.assertEqual(device_code_obj.client.client_id, self._tv_client_id)

    def test_device_authorization_with_charset_in_content_type(self):
        response = self.client.post(reverse('oauth2:device_authorization'),
                                    data=urlencode({'client_id': self._tv_client_id, 'scope': 'openid'}),
                                    content_type='application/x-www-form-urlencoded; charset=utf-8')
        self.assertEqual(response.status_code, 200)

    def test_device_authorization_without_content_type_is_rejected(self):
        response = self.client.generic('POST', reverse('oauth2:device_authorization'), data=b'', content_type='')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_request')

    def test_device_authorization_unknown_client_is_rejected(self):
        response = self.device_authorization_request(client_id="0" * 32)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_client")
        self.assertEqual(DeviceCode.objects.count(), 0)

    def test_device_authorization_non_native_client_is_rejected(self):
        # implicit flow client, not confidential but also not allowed to use the device grant
        response = self.device_authorization_request(client_id="92d7d9d71d5d41caa652080c19aaa6d8")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'unauthorized_client')
        self.assertEqual(DeviceCode.objects.count(), 0)

    def test_device_authorization_client_without_opt_in_is_rejected(self):
        Client.objects.filter(uuid=self._tv_client_id).update(device_authorization_grant=False)
        response = self.device_authorization_request()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'unauthorized_client')
        self.assertEqual(DeviceCode.objects.count(), 0)

    def test_token_client_without_opt_in_is_rejected(self):
        # the opt-in was removed after the device code was issued
        data = self.device_authorization_request().json()
        Client.objects.filter(uuid=self._tv_client_id).update(device_authorization_grant=False)
        token_response = self.poll_token(data['device_code'])
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.json()['error'], 'unauthorized_client')

    def test_admin_form_opt_in_only_for_native_clients(self):
        fields = ['name', 'type', 'client_secret', 'scopes', 'device_authorization_grant']
        form_class = modelform_factory(Client, form=ClientAdminForm, fields=fields)

        client = Client.objects.get(uuid=self._client_id)  # a confidential 'web' client
        data = {field: getattr(client, field) for field in fields}
        data['device_authorization_grant'] = True
        form = form_class(data=data, instance=client)
        self.assertFalse(form.is_valid())
        self.assertIn('device_authorization_grant', form.errors)

        client = Client.objects.get(uuid=self._tv_client_id)  # a public 'native' client
        data = {field: getattr(client, field) for field in fields}
        form = form_class(data=data, instance=client)
        self.assertTrue(form.is_valid(), form.errors)

    def selfservice_client_form(self, client_type, device_authorization_grant=True, redirect_uris=''):
        tv_client = Client.objects.get(uuid=self._tv_client_id)
        data = {
            'application': tv_client.application.pk,
            'uuid': str(uuid.uuid4()),
            'name': 'device client',
            'type': client_type,
            'client_secret': 'secret' if client_type in ['web', 'service'] else '',
            'scopes': ['openid'],
            'redirect_uris': redirect_uris,
            'is_active': True,
        }
        if device_authorization_grant:
            data['device_authorization_grant'] = 'on'
        return ClientForm(data=data, initial={}, user=get_user_model().objects.get(username='GunnarScherf'))

    def test_selfservice_native_client_with_device_grant_needs_no_redirect_uri(self):
        form = self.selfservice_client_form('native')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data['device_authorization_grant'])

        form = self.selfservice_client_form('native', device_authorization_grant=False)
        self.assertFalse(form.is_valid())
        self.assertIn('redirect_uris', form.errors)

    def test_selfservice_device_grant_only_for_native_clients(self):
        form = self.selfservice_client_form('web', redirect_uris='https://example.com/')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['device_authorization_grant'])

    def test_cleartokens_deletes_expired_device_codes(self):
        data = self.device_authorization_request().json()
        expired = self.device_authorization_request().json()
        DeviceCode.objects.filter(device_code=expired['device_code']).update(expires_at=timezone.now() - timedelta(seconds=1))
        call_command('cleartokens')
        self.assertEqual(list(DeviceCode.objects.values_list('device_code', flat=True)), [data['device_code']])

    def test_device_authorization_scope_not_allowed_for_client_is_rejected(self):
        response = self.device_authorization_request(scope="openid profile role")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_scope')
        self.assertEqual(DeviceCode.objects.count(), 0)

    def test_token_without_device_code_is_invalid_request(self):
        response = self.client.post(reverse('oauth2:token'), {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'client_id': self._tv_client_id,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_request')

    def test_token_with_dashed_client_id(self):
        data = self.device_authorization_request().json()
        token_response = self.poll_token(data['device_code'], client_id=str(uuid.UUID(self._tv_client_id)))
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.json()['error'], 'authorization_pending')

    def test_token_is_authorization_pending_before_approval(self):
        data = self.device_authorization_request().json()
        token_response = self.poll_token(data['device_code'])
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.json()['error'], 'authorization_pending')

    def test_token_slow_down_on_rapid_polling(self):
        data = self.device_authorization_request().json()
        first_poll = self.poll_token(data['device_code'])
        self.assertEqual(first_poll.json()['error'], 'authorization_pending')
        second_poll = self.poll_token(data['device_code'])
        self.assertEqual(second_poll.json()['error'], 'slow_down')

    def test_full_flow_approve_then_get_token(self):
        data = self.device_authorization_request(scope="openid profile email offline_access").json()

        self.client.login(username='GunnarScherf', password='gsf')
        approve_response = self.client.post(reverse('oauth2:device'), {
            'user_code': data['user_code'],
            'approve': '1',
        })
        self.assertEqual(approve_response.status_code, 200)
        self.logout()

        token_response = self.poll_token(data['device_code'])
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()
        self.assertIn('access_token', token)
        self.assertIn('refresh_token', token)
        self.assertIn('id_token', token)

        # device codes are single-use: the row is gone, and polling again fails
        self.assertFalse(DeviceCode.objects.filter(device_code=data['device_code']).exists())
        second_poll = self.poll_token(data['device_code'])
        self.assertEqual(second_poll.status_code, 400)
        self.assertEqual(second_poll.json()['error'], 'invalid_grant')

    def approve(self, user_code):
        return self.client.post(reverse('oauth2:device'), {'user_code': user_code, 'approve': '1'})

    def test_token_acr_with_otp_device(self):
        # the OTP device the user signed in with is kept for the acr claim, like for the authorization code
        data = self.device_authorization_request().json()
        user = get_user_model().objects.get(username='GunnarScherf')
        otp_device = Device.objects.create(user=user, name='test', confirmed=True)
        DeviceCode.objects.filter(device_code=data['device_code']).update(
            user=user, otp_device=otp_device, status=DeviceCode.STATUS_APPROVED)
        token = self.poll_token(data['device_code']).json()
        self.assertEqual(crypt.loads_jwt(token['access_token'])['acr'], '2')
        self.assertEqual(crypt.loads_jwt(token['id_token'])['acr'], '2')

    def test_dashed_client_id_keeps_aud(self):
        # like for the authorization code: the aud claim of the id_token is the client_id as sent
        dashed_client_id = str(uuid.UUID(self._tv_client_id))
        data = self.device_authorization_request(client_id=dashed_client_id).json()
        self.client.login(username='GunnarScherf', password='gsf')
        self.approve(data['user_code'])
        self.logout()
        token_response = self.poll_token(data['device_code'], client_id=dashed_client_id)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(crypt.loads_jwt(token_response.json()['id_token'])['aud'], dashed_client_id)

    def test_token_acr_without_otp_device(self):
        data = self.device_authorization_request().json()
        self.client.login(username='GunnarScherf', password='gsf')
        self.approve(data['user_code'])
        self.logout()
        token = self.poll_token(data['device_code']).json()
        self.assertEqual(crypt.loads_jwt(token['access_token'])['acr'], '1')

    def test_user_code_input_is_normalized(self):
        data = self.device_authorization_request().json()
        self.client.login(username='GunnarScherf', password='gsf')
        typed = ' ' + data['user_code'].replace('-', ' ').lower() + ' '
        response = self.approve(typed)
        self.assertContains(response, "You're signed in")
        self.assertEqual(DeviceCode.objects.get(device_code=data['device_code']).status, DeviceCode.STATUS_APPROVED)

    def test_code_can_only_be_confirmed_once(self):
        data = self.device_authorization_request().json()
        self.client.login(username='GunnarScherf', password='gsf')
        self.approve(data['user_code'])
        response = self.approve(data['user_code'])
        self.assertContains(response, 'not valid')
        response = self.client.post(reverse('oauth2:device'), {'user_code': data['user_code'], 'deny': '1'})
        self.assertContains(response, 'not valid')
        self.assertEqual(DeviceCode.objects.get(device_code=data['device_code']).status, DeviceCode.STATUS_APPROVED)

    def test_device_page_rejects_code_of_client_without_opt_in(self):
        data = self.device_authorization_request().json()
        Client.objects.filter(uuid=self._tv_client_id).update(device_authorization_grant=False)
        self.client.login(username='GunnarScherf', password='gsf')
        response = self.approve(data['user_code'])
        self.assertContains(response, 'not valid')
        self.assertEqual(DeviceCode.objects.get(device_code=data['device_code']).status, DeviceCode.STATUS_PENDING)

    def test_deny_blocks_the_token(self):
        data = self.device_authorization_request().json()

        self.client.login(username='GunnarScherf', password='gsf')
        deny_response = self.client.post(reverse('oauth2:device'), {
            'user_code': data['user_code'],
            'deny': '1',
        })
        self.assertEqual(deny_response.status_code, 200)
        self.logout()

        token_response = self.poll_token(data['device_code'])
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.json()['error'], 'access_denied')

    def test_expired_device_code_is_rejected(self):
        data = self.device_authorization_request().json()
        DeviceCode.objects.filter(device_code=data['device_code']).update(
            expires_at=timezone.now() - timedelta(seconds=1))

        token_response = self.poll_token(data['device_code'])
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.json()['error'], 'expired_token')

    def test_device_page_rejects_unknown_user_code(self):
        self.client.login(username='GunnarScherf', password='gsf')
        response = self.client.get(reverse('oauth2:device'), {'user_code': 'ZZZZ-ZZZZ'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not valid')


@override_settings(SSO_DEVICE_AUTHORIZATION_GRANT=False)
class DeviceCodeGrantDisabledTests(OAuth2BaseTestCase):
    # the device authorization grant is behind the feature flag SSO_DEVICE_AUTHORIZATION_GRANT (default False)
    _tv_client_id = "3f6a9b6b1a8940e6a3f0a2f7f3f2e1a1"

    def test_device_authorization_endpoint_not_found(self):
        response = self.client.post(reverse('oauth2:device_authorization'),
                                    data=urlencode({'client_id': self._tv_client_id}),
                                    content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(DeviceCode.objects.count(), 0)

    def test_device_page_not_found(self):
        # also for anonymous users, so there is no redirect to the login page
        response = self.client.get(reverse('oauth2:device'))
        self.assertEqual(response.status_code, 404)
        self.client.login(username='GunnarScherf', password='gsf')
        response = self.client.get(reverse('oauth2:device'), {'user_code': 'ABCD-EFGH'})
        self.assertEqual(response.status_code, 404)

    def test_token_unsupported_grant_type(self):
        # a device code from the time the flag was enabled must not be redeemable
        user = get_user_model().objects.get(username='GunnarScherf')
        DeviceCode.objects.create(client=Client.objects.get(uuid=self._tv_client_id), user=user,
                                  device_code='device-code', user_code='ABCD-EFGH', scopes='openid',
                                  status=DeviceCode.STATUS_APPROVED,
                                  expires_at=timezone.now() + timedelta(minutes=5))
        response = self.client.post(reverse('oauth2:token'), {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'client_id': self._tv_client_id,
            'device_code': 'device-code',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'unsupported_grant_type')

    def test_selfservice_client_form_has_no_device_grant_field(self):
        form = ClientForm(initial={}, user=get_user_model().objects.get(username='GunnarScherf'))
        self.assertNotIn('device_authorization_grant', form.fields)

    def test_discovery(self):
        response = self.client.get(reverse('openid-configuration'))
        self.assertNotIn('device_authorization_endpoint', response.json())
        self.assertEqual(response.json()['grant_types_supported'],
                         ['authorization_code', 'implicit', 'refresh_token', 'client_credentials', 'password'])
        cache.clear()  # the discovery document is cached
        with self.settings(SSO_DEVICE_AUTHORIZATION_GRANT=True):
            response = self.client.get(reverse('openid-configuration'))
            self.assertTrue(response.json()['device_authorization_endpoint'].endswith(
                reverse('oauth2:device_authorization')))
            self.assertIn('urn:ietf:params:oauth:grant-type:device_code', response.json()['grant_types_supported'])
