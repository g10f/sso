# -*- coding: utf-8 -*-
import json
from uuid import uuid4

from django.urls import reverse
from uritemplate import expand

from sso.oauth2.tests import OAuth2BaseTestCase


def address(addressee, country='DE', street_address='', region='', address_type='home'):
    return {
        'address_type': address_type,
        'addressee': addressee,
        'region': region,
        'country': country,
        'street_address': street_address
    }


def phone(phone, phone_type='home', primary=True):
    return {
        'phone': phone,
        'primary': primary,
        'phone_type': phone_type
    }


class ApiTests(OAuth2BaseTestCase):
    """
    data = json.dumps({
        'given_name': 'Test',
        'family_name': 'Myfamily',
        'email': 'new@g10f.de',
        'organisations': {'31664dd38ca4454e916e55fe8b1f0746': {}}
    })
    """
    data = {
        'org_id': '31664dd38ca4454e916e55fe8b1f0745',
        'user_id': 'a8992f0348634f76b0dac2de4e4c83ee',
        'iso2_code': 'DE',
        'country': 'DE',
        'country_code': 'DE',
        'region_id': '0ebf2537fc664b7db285ea773c981404',
        'country_group_id': 'f6b34d1cee944138800980fe48a2b26f',
        'association_id': 'bad2e6edff274f2f900ff3dbb26e38ce'
    }

    def get_url_from_api_home(self, name, kwargs=None):
        if kwargs is None:
            kwargs = {}
        response = self.client.get(reverse('api:home'))
        home = response.json()
        return expand(home[name], kwargs)

    def test_entry_point(self):
        response = self.client.get(reverse('api:home'))
        home = response.json()
        authorization = self.get_authorization(client_id="1811f02ed81b43b5bee1afe031e6198e", username="GlobalAdmin", password="secret007", scope="users")
        self.longMessage = True
        for entry in home:
            if entry[0] != '@':
                url = expand(home[entry], self.data)
                response = self.client.get(url, HTTP_AUTHORIZATION=authorization)
                if 'application/json' in response['Content-Type'].split(';'):
                    self.assertNotIn('error', response.json(), url)
                self.assertEqual(response.status_code, 200, "got %s on %s" % (response.status_code, url))

    def test_organisation_list(self):
        organisations_url = self.get_url_from_api_home('organisations')
        authorization = self.get_authorization(client_id="1811f02ed81b43b5bee1afe031e6198e", username="CountryAdmin", scope="users")
        response = self.client.get(organisations_url, HTTP_AUTHORIZATION=authorization)
        organisations = response.json()
        self.assertNotIn('error', organisations)

        # get the details url of the first member of the collection
        details_url = organisations['member'][0]['@id']
        response = self.client.get(details_url, HTTP_AUTHORIZATION=authorization)
        organisation = response.json()
        self.assertNotIn('error', organisations)

    def test_user_list(self):
        users_url = self.get_url_from_api_home('users')

        authorization = self.get_authorization(client_id="1811f02ed81b43b5bee1afe031e6198e", username="CountryAdmin", scope="users")
        # get user list
        response = self.client.get(users_url, HTTP_AUTHORIZATION=authorization)
        users = response.json()
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
        user = response.json()
        user['email'] = 'abc@g10f.de'
        user['birth_date'] = '1964-09-01'
        user_url = expand('http://testserver/api/v2/users/{uuid}/', {'uuid': uuid4().hex})
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        user = response.json()
        self.assertNotIn('error', user)

        # add address to  existing user (failing)
        user['addresses'] = {uuid4().hex: address('Test Address', address_type='work')}
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = response.json()
        self.assertIn('scope \"address\" is missing', response_obj['error_description'])

        # add phone to existing user (failing)
        user['phone_numbers'] = {uuid4().hex: phone('+49 123456')}
        del user['addresses']
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = response.json()
        self.assertIn('scope \"phone\" is missing', response_obj['error_description'])

        # get access_token with address and phone scopes
        authorization = self.get_authorization(client_id="81062e2af4db4669a721d37d1ed7c058", username="CountryAdmin", scope="users address phone")

        # add address to  existing user (success)
        del user['phone_numbers']
        work_uuid = uuid4().hex
        home_uuid = uuid4().hex
        addresses = {
            work_uuid: address('Work Address', address_type='work'),
            home_uuid: address('Home Address', address_type='home')
        }
        user['addresses'] = addresses
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = response.json()
        self.assertNotIn('error', response_obj)

        # remove work address
        addresses = {
            home_uuid: address('Home Address', address_type='home')
        }
        user['addresses'] = addresses
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = response.json()
        self.assertNotIn('error', response_obj)

        # add phone to existing user (success)
        user['phone_numbers'] = {uuid4().hex: phone('+49 123456')}
        del user['addresses']
        response = self.client.put(user_url, json.dumps(user), HTTP_AUTHORIZATION=authorization)
        response_obj = response.json()
        self.assertNotIn('error', response_obj)
