# -*- coding: utf-8 -*-
import json
from uuid import uuid4

from django.core.urlresolvers import reverse
from uritemplate import expand

from sso.oauth2.tests import OAuth2BaseTestCase


def new_address(addressee, country='DE', street_address='', region='', address_type='home'):
    return {
        uuid4().hex:
        {
            'address_type': address_type,
            'addressee': addressee,
            'region': region,
            'country': country,
            'street_address': street_address
        }
    }

def new_phone(phone, phone_type='home', primary=True):
    return {
        uuid4().hex: 
        {
            'phone': phone,
            'primary': primary,
            'phone_type': phone_type
        }
    }


class ApiTests(OAuth2BaseTestCase):
    data = json.dumps({
        'given_name': 'Test',
        'family_name': 'Myfamily',
        'email': 'new@g10f.de',
        'organisations': {'31664dd38ca4454e916e55fe8b1f0746': {}}
    })
    
    def test_userlist(self):
        response = self.client.get(reverse('api:home'))
        home = json.loads(response.content)
        users_url = expand(home['users'], {})
        
        authorization = self.get_authorization(client_id="1811f02ed81b43b5bee1afe031e6198e", username="CountryAdmin", scope="users")
        # get user list
        response = self.client.get(users_url, HTTP_AUTHORIZATION=authorization)
        users = json.loads(response.content)
        self.assertNotIn('error', users)
        operation = [{
            '@type': "CreateResourceOperation",
            'template': 'http://testserver/api/v2/users/{uuid}/',
            'method': "PUT"
        }]
        self.assertEqual(users['operation'], operation)
        
        # create new user
        user_url = users['member'][0]['@id']
        response = self.client.get(user_url, HTTP_AUTHORIZATION=authorization)
        user = json.loads(response.content)
        user['email'] = 'abc@g10f.de'
        user['birth_date'] = '1964-09-01'
        user_url = expand('http://testserver/api/v2/users/{uuid}/', {'uuid': uuid4().hex})
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        user = json.loads(response.content)
        self.assertNotIn('error', user)
        
        # add address to  existing user (failing)
        user['addresses'] = new_address('Test Address', address_type='work')
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = json.loads(response.content)
        self.assertIn('scope \"address\" is missing', response_obj['error_description'])

        # add phone to existing user (failing)
        user['phone_numbers'] = new_phone('123456')
        del user['addresses']
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = json.loads(response.content)
        self.assertIn('scope \"phone\" is missing', response_obj['error_description'])

        # get access_token with address and phone scopes
        authorization = self.get_authorization(client_id="81062e2af4db4669a721d37d1ed7c058", username="CountryAdmin", scope="users address phone")

        # add address to  existing user (success)
        del user['phone_numbers']
        user['addresses'] = new_address('Test Address', address_type='work')
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = json.loads(response.content)
        self.assertNotIn('error', response_obj)

        # add phone to existing user (success)
        user['phone_numbers'] = new_phone('123456')
        del user['addresses']
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = json.loads(response.content)
        self.assertNotIn('error', response_obj)
