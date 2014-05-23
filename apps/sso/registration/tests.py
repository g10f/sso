# -*- coding: utf-8 -*-
import urlparse
import re
import os

from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse


class RegistrationTest(TestCase):
    fixtures = ['initial_data.json', 'app_roles.json', 'test_l10n_data.xml', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']

    def setUp(self):
        os.environ['RECAPTCHA_TESTING'] = 'True'
        self.client = Client()
    
    def tearDown(self):
        del os.environ['RECAPTCHA_TESTING']
    
    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertGreater(len(outbox), 0)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[-1].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlparse.urlsplit(urls[0])  # @UnusedVariable
        return path

    def test_registration_register_by_bot(self):
        """
        User self registration with email validation
        """        
        data = {
            'email': 'test2@g10f.de',
            'email2': 'test2@g10f.de',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'known_person1_first_name': 'known_person1_first_name',
            'known_person2_first_name': 'known_person2_first_name',
            'known_person1_last_name': 'known_person1_last_name',
            'known_person2_last_name': 'known_person2_last_name',
            'country': 81,
            'city': 'Megacity',
            'recaptcha_response_field': 'xyz'
        }
        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertFormError(response, 'form', 'captcha', ['Incorrect, please try again.'])
    
    def test_registration_register(self):
        """
        User self registration with email validation
        """        
        response = self.client.get(reverse('registration:registration_register'))
        self.assertEqual(response.status_code, 200)

        data = {
            'email': 'test2@g10f.de',
            'email2': 'test2@g10f.de',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'known_person1_first_name': 'known_person1_first_name',
            'known_person2_first_name': 'known_person2_first_name',
            'known_person1_last_name': 'known_person1_last_name',
            'known_person2_last_name': 'known_person2_last_name',
            'about_me': 'Test',
            'country': 81,
            'city': 'Megacity',
            'organisation': 1,
            'recaptcha_response_field': 'PASSED'
      
        }
        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertNotContains(response, 'has-error')
        
        # captcha is only displayed once.
        # the second time a signed value is used
        del data['recaptcha_response_field']        
        data['state'] = response.context['form'].data['state']
        
        data[response.context['stage_field']] = "2"
        data[response.context['hash_field']] = response.context['hash_value']
        
        response = self.client.post(reverse('registration:registration_register'), data=data)
        print response.content
        self.assertEqual(response.status_code, 302)

        path = self.get_url_path_from_mail()
        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)
        
        response = self.client.get(response['Location'])
        self.assertEqual(response.status_code, 200)

        """
        Admin activates the registered user
        """
        path = self.get_url_path_from_mail()
        self.client.login(username='GlobalAdmin', password='secret007')
        
        #data['is_verified'] = 'on'
        data['username'] = "TestUser"
        data['verified_by_user'] = 1
        data['organisations'] = 1
        
        response = self.client.post(path, data=data)
        self.assertEqual(response.status_code, 302)
        # check if the user got an email for creating the password
        outbox = getattr(mail, 'outbox')
        self.assertNotEqual(outbox[-1].subject.find('Set your password'), -1) 
