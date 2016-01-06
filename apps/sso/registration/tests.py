# -*- coding: utf-8 -*-
from django.utils.six.moves.urllib.parse import urlsplit
import re
import os

from django.core import mail
from django.test import TestCase
from django.core.urlresolvers import reverse

from sso.registration import default_username_generator
from sso.organisations.models import Organisation
from sso.test.client import SSOClient


class RegistrationTest(TestCase):
    fixtures = ['roles.json', 'app_roles.json', 'test_l10n_data.xml', 'test_organisation_data.json', 'test_app_roles.json',
                'test_user_data.json']

    def setUp(self):
        os.environ['NORECAPTCHA_TESTING'] = 'True'
        self.client = SSOClient()
    
    def tearDown(self):
        del os.environ['NORECAPTCHA_TESTING']
    
    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertGreater(len(outbox), 0)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[-1].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlsplit(urls[0])  # @UnusedVariable
        return path

    def test_default_username_generator(self):
        username = default_username_generator("Gunnar", "Scherf")
        self.assertEqual(username, "GunnarScherf1")

        username = default_username_generator("GunnarXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", "Scherf")
        self.assertEqual(username, "GunnarXXXXXXXXXXXXXXXXXXXXXXX")
                
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
            'g-recaptcha-response': 'xyz'
        }
        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertFormError(response, 'form', 'captcha', ['Incorrect, please try again.'])

    def registration(self):
        """
        User self registration with email validation
        """
        response = self.client.get(reverse('registration:registration_register'))
        self.assertEqual(response.status_code, 200)
        organisation = Organisation.objects.filter(is_active=True).first()

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
            'organisation': organisation.pk,
            'g-recaptcha-response': 'PASSED'

        }
        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertNotContains(response, 'has-error')

        # captcha is only displayed once.
        # the second time a signed value is used
        del data['g-recaptcha-response']
        data['state'] = response.context['form'].data['state']

        data[response.context['stage_field']] = "2"
        data[response.context['hash_field']] = response.context['hash_value']

        response = self.client.post(reverse('registration:registration_register'), data=data)
        print(response.content)
        self.assertEqual(response.status_code, 302)

        path = self.get_url_path_from_mail()
        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(response['Location'])
        self.assertEqual(response.status_code, 200)

        # admin reads his mail box
        outbox = getattr(mail, 'outbox')
        fullname = 'first_name' + ' ' + 'last_name'
        self.assertNotEqual(outbox[-1].subject.find('Registration of %s completed' % fullname), -1)
        path = self.get_url_path_from_mail()

        return path, data

    def test_registration_delete(self):
        path, data = self.registration()

        # admin logs in
        self.client.login(username='GlobalAdmin', password='secret007')

        # get the registration form
        response = self.client.get(path)

        # get the delete form url
        pk = re.findall(r'registrations/delete/(?P<pk>\d+)/', response.content)[0]
        # post the delete form
        path = reverse('registration:delete_user_registration', args=[pk])
        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)

    def test_registration_register(self):
        path, data = self.registration()

        # admin logs in
        self.client.login(username='GlobalAdmin', password='secret007')

        # admin activates the account
        data['username'] = "TestUser"
        response = self.client.post(path, data=data)
        self.assertEqual(response.status_code, 302)

        # the user got an email for creating the password
        outbox = getattr(mail, 'outbox')
        self.assertNotEqual(outbox[-1].subject.find('Set your password'), -1)
