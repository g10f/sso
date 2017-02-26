# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.test import TestCase
from sso.accounts.models import User
from sso.organisations.models import OrganisationCountry
from sso.test.client import SSOClient


class AccountsTest(TestCase):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']

    def setUp(self):
        self.client = SSOClient()

    def tearDown(self):
        pass

    def test_app_admin_user_list(self):
        result = self.client.login(username='ApplicationAdmin', password='gsf')
        self.assertEqual(result, True)

        response = self.client.get(reverse('accounts:app_admin_user_list'), data={'country': OrganisationCountry.objects.first().pk})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('accounts:app_admin_user_list'), data={'country': 99999})
        self.assertEqual(response.status_code, 200)

    def test_app_admin_update_user(self):
        result = self.client.login(username='ApplicationAdmin', password='gsf')
        self.assertEqual(result, True)

        # User.objects.get()
        response = self.client.get(reverse('accounts:app_admin_user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('accounts:app_admin_update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'}))

        response = self.client.get(reverse('accounts:app_admin_update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'}))
        self.assertEqual(response.status_code, 200)
