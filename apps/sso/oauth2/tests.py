import base64
import hashlib
from time import sleep
from urllib.parse import urlsplit

from django.http import QueryDict, SimpleCookie
from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string
from sso.test.client import SSOClient
from . import crypt


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
        self.assertEqual(fragment_dict['expires_in'], '3600')
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
        self.assertIn('31664dd38ca4454e916e55fe8b1f0745', user_info['organisations'])

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
        self.assertIn('31664dd38ca4454e916e55fe8b1f0745', user_info['organisations'])

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
