# -*- coding: utf-8 -*-
import urlparse
import json
import base64
from time import sleep

from django.http import QueryDict, SimpleCookie
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

def get_query_dict(url):        
    scheme, netloc, path, query_string, fragment = urlparse.urlsplit(url)  # @UnusedVariable
    query_dict = QueryDict(query_string).copy()
    return query_dict

def urlsafe_b64decode(b64string):
    # Guard against unicode strings, which base64 can't handle.
    b64string = b64string.encode('ascii')
    padded = b64string + '=' * (4 - len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)

def load_jwt(jwt, audience=None):
    """
    load jwt without signature check
    """
    segments = jwt.split('.')

    if (len(segments) != 3):
        raise Exception('id_token_error: Wrong number of segments in token: %s' % jwt)
    
    #signed = '%s.%s' % (segments[0], segments[1])
    #signature = urlsafe_b64decode(segments[2])

    # Parse token.
    json_body = urlsafe_b64decode(segments[1])
    try:
        parsed = json.loads(json_body)
    except:
        raise Exception('id_token_error: Can\'t parse token: %s' % json_body)

    # Check audience.
    if audience is not None:
        aud = parsed.get('aud')
        if aud is None:
            raise Exception('id_token_error: No aud field in token: %s' % json_body)
        if aud != audience:
            raise Exception('id_token_error: Wrong recipient, %s != %s: %s' % (aud, audience, json_body))

    return parsed

class OAuth2BaseTestCase(TestCase):
    fixtures = ['initial_data.json', 'app_roles.json', 'test_user_data.json', 'test_oauth2_data.json']
    _client_id = "ec1e39cbe3e746c787b770ace4165d13"
    _state = 'eyJub25jZSI6Ik1sSllaUlc3VWdGdyIsInByb3ZpZGVyIjoyLCJuZXh0IjoiLyJ9'

    def setUp(self):
        self.client = Client()
    
    def logout(self):
        self.client.logout()
        self.client.cookies = SimpleCookie()
        
    def login_and_get_code(self, client_id=None, max_age=None, wait=0, username='GunnarScherf', password='gsf'):       
        self.client.login(username=username, password=password)
        if wait > 0:
            sleep(wait)
 
        authorize_data = {
            'scope': "openid profile email",
            'state': self._state,
            'redirect_uri': "http://localhost",
            'response_type': "code",
            'client_id': client_id if client_id else self._client_id,
        }
        if max_age:
            authorize_data['max_age'] = max_age
            
        response = self.client.get(reverse('oauth2:authorize'), data=authorize_data)
        self.assertEqual(response.status_code, 302)
        query_dict = get_query_dict(response['Location'])
        
        self.assertIn('code', query_dict)
        self.assertDictContainsSubset({'state': self._state}, query_dict)
        return query_dict['code']

    def get_authorization(self, client_id=None, username='GunnarScherf', password='gsf'):
        code = self.login_and_get_code(client_id, username=username, password=password)
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': client_id if client_id else self._client_id,
            'code': code
        }
        token_response = self.client.post(reverse('oauth2:token'), token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response['Content-Type'], 'application/json;charset=UTF-8')
        
        token = json.loads(token_response.content)
        self.logout()  
        return 'Bearer %s' % token['access_token']
    

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
        self.assertDictContainsSubset({'error': 'mismatching_redirect_uri'}, query_dict)
        
        self.assertEqual(urlparse.urlsplit(response['Location'])[2], reverse('oauth2:oauth2_error'))
        
        response = self.client.get(response['Location'])
        self.assertEqual(response.context['error'], 'mismatching_redirect_uri')

    def test_login_and_get_code_max_age_failure(self):
        self.client.login(username='GunnarScherf', password='gsf')
        max_age = 2
        sleep(max_age)
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
        path = urlparse.urlsplit(response['Location'])[2]
        self.assertEqual(path, reverse('accounts:login'))
        
    def test_get_token(self):
        code = self.login_and_get_code()
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://localhost",
            'client_secret': "geheim",
            'client_id': self._client_id,
            'code': code,
        }
        token_response = self.client.post(reverse('oauth2:token'), token_data)
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response['Content-Type'], 'application/json;charset=UTF-8')
        self.assertEqual(token_response['Cache-Control'], 'no-store')
        self.assertEqual(token_response['Pragma'], 'no-cache')
        
        token = json.loads(token_response.content)  
        self.assertIn('access_token', token)
        self.assertIn('id_token', token)
        self.assertIn('expires_in', token)
        self.assertIn('scope', token)
        self.assertIn('token_type', token)

        self.assertDictContainsSubset({'scope': 'openid profile email', 'token_type': 'Bearer'}, token)
        
        id_token = load_jwt(token['id_token'])
        self.assertIn('iss', id_token)
        self.assertIn('sub', id_token)
        self.assertIn('aud', id_token)
        self.assertIn('exp', id_token)
        self.assertIn('iat', id_token)
        self.assertIn('email', id_token)
        self.assertIn('name', id_token)
        self.assertIn('roles', id_token)
        
        expected = {
            'iss': 'testserver', 
            'sub': 'a8992f0348634f76b0dac2de4e4c83ee',  # user_id 
            'aud': self._client_id, 
            'email': 'gunnar@g10f.de', 
            'name': 'GunnarScherf'
        }
        self.assertDictContainsSubset(expected, id_token)
        
        roles = id_token['roles'].split()
        self.assertIn('Admin', roles)
        self.assertIn('Staff', roles)
                
        authorization = 'Bearer %s' % token['access_token']
        self.logout()
        
        response = self.client.get(reverse('api:v1_index'))
        index = json.loads(response.content)
        
        # no authentication
        response = self.client.get(index['links']['me']['href'])
        self.assertEqual(response.status_code, 401)

        # valid authentication
        response = self.client.get(index['links']['me']['href'], HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 200)
        user_info = json.loads(response.content)
        self.assertEqual(user_info['family_name'], 'Scherf')
        self.assertIn('31664dd38ca4454e916e55fe8b1f0745', user_info['organisations'])
        
        # this is only for global admin accounts  
        response = self.client.get(reverse('api:v1_users'), HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 401)

    def test_get_token_failure(self):
        code = self.login_and_get_code()
        token_data = {
            'grant_type': "authorization_code",
            'redirect_uri': "http://error_domain",
            'client_secret': "geheim",
            'client_id': self._client_id,
            'code': code
        }
        
        token_response = self.client.post(reverse('oauth2:token'), token_data)
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response['Content-Type'], 'application/json;charset=UTF-8')
        
        token = json.loads(token_response.content)
        self.assertIn('error', token)
        self.assertDictContainsSubset({'error': 'access_denied'}, token)

        token_data['redirect_uri'] = "http://localhost"
        token_data['code'] = "wrong_code"
        
        token_response = self.client.post(reverse('oauth2:token'), token_data)
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response['Content-Type'], 'application/json;charset=UTF-8')
        
        token = json.loads(token_response.content)  
        self.assertIn('error', token)
        self.assertDictContainsSubset({'error': 'invalid_grant'}, token)
