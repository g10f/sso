# -*- coding: utf-8 -*-
import json
from django.core.urlresolvers import reverse
from uritemplate import expand

from http.http_status import *  # @UnusedWildImport

from sso.oauth2.tests import OAuth2BaseTestCase

class ApiTests(OAuth2BaseTestCase):
    data = json.dumps({
        'given_name': 'Test',
        'family_name': 'Myfamily',
        'email': 'new@g10f.de',
        'organisations': {'31664dd38ca4454e916e55fe8b1f0746': {}}
    })
    
    def test_v2_userlist(self):
        response = self.client.get(reverse('api:home'))
        home = json.loads(response.content)
        users_url = expand(home['users'], {})
        
        authorization = self.get_authorization(scope="openid profile email users")
        response = self.client.get(users_url, HTTP_AUTHORIZATION=authorization)
        users = json.loads(response.content)
        self.assertNotIn('error', users)        

    def test_v1_put_and_delete_user(self):
        authorization = self.get_authorization()
        uri = reverse('api:v1_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})        
        response = self.client.put(uri, data=self.data, HTTP_AUTHORIZATION=authorization)
        # client_id not allowed
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED) 
        
        authorization = self.get_authorization(client_id='68bfae12a58541548def243e223053fb')
        response = self.client.put(uri, data=self.data, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, HTTP_200_OK)
        userinfo = json.loads(response.content)
        
        # given_name, family_name and email can not be changed
        self.assertEqual(userinfo['given_name'], 'Gunnar')
        self.assertEqual(userinfo['family_name'], 'Scherf')
        self.assertEqual(userinfo['email'], 'gunnar@g10f.de')
        
        # organisation can be changed
        organisations = userinfo['organisations']
        self.assertEqual(len(organisations), 1)
        self.assertIn('31664dd38ca4454e916e55fe8b1f0746', organisations)
        
        response = self.client.delete(uri, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_v1_put_user_failure(self):
        self.client.login(username='GunnarScherf', password='gsf')
        uri = reverse('api:v1_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})
        response = self.client.get(uri)
        self.assertEqual(response.status_code, HTTP_200_OK)
        
        response = self.client.put(uri, data=self.data)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED) 

    def test_v1_get_user_list(self):
        authorization = self.get_authorization()
        uri = reverse('api:v1_users')        
        response = self.client.get(uri, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)  # Standard user is not allowed to query all users

        # login as user with the rigth to change all users
        authorization = self.get_authorization(username="GlobalAdmin", password="secret007")
        response = self.client.get(uri, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, HTTP_200_OK)
        
        # filter for usernames 
        response = self.client.get(uri, data={'q': 'unna'}, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, HTTP_200_OK)
        userlist = json.loads(response.content)
        self.assertEqual(len(userlist['collection']), 1)
