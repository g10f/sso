# -*- coding: utf-8 -*-
import urlparse
import re

from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse


class RegistrationTest(TestCase):
    fixtures = ['initial_data.json', 'app_roles.json', 'test_user_data.json', 'test_l10n_data.xml']

    def setUp(self):
        self.client = Client()
    
    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertGreater(len(outbox), 0)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[-1].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlparse.urlsplit(urls[0])  # @UnusedVariable
        return path

    def test_registration_register(self):
        """
        User self registration with email validation
        """        
        response = self.client.get(reverse('registration:registration_register'))
        self.assertEqual(response.status_code, 200)

        data = {
            'email': 'test2@g10f.de',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'known_person1': 'known_person1',
            'known_person2': 'known_person2',
            'purpose': 'Test',
            'country': 81,
            'phone': '123456',
            'organisation': 1         
        }
        response = self.client.post(reverse('registration:registration_register'), data=data)
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
        data['verified_by_user'] = 1
        data['organisations'] = 1
        
        response = self.client.post(path, data=data)
        self.assertEqual(response.status_code, 302)
        # check if the user got an email for creating the password
        outbox = getattr(mail, 'outbox')
        self.assertNotEqual(outbox[-1].subject.find('Wähle Dein Passwort'), -1) 
