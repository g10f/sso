# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse
from sso.organisations.models import OrganisationCountry, Organisation
from sso.test.client import SSOClient


class OrganisationssTest(TestCase):
    fixtures = ['roles.json', 'app_roles.json', 'test_l10n_data.json', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']

    def setUp(self):
        self.client = SSOClient()
    
    def tearDown(self):
        pass

    def test_add_organisation_by_country_admin(self):
        self.client.login(username='CountryAdmin', password='gsf')
        response = self.client.get(reverse('organisations:organisation_create'))
        
        self.assertEqual(response.status_code, 200)
        # CountryAdmin is admin of County 81
        country = OrganisationCountry.objects.get(country__id=81).country
        countries = response.context['form'].fields['country'].queryset
        self.assertEqual(len(countries), 1)
        self.assertEqual(country, countries[0])
        
        # create a new center
        data = {
            'name': 'New Center',
            'center_type': '2',
            'country': 81,
            'email_value': 'newcenter' + settings.SSO_ORGANISATION_EMAIL_DOMAIN,
            'email_forward': 'test@g10f.de',
            'coordinates_type': 3,
            'is_active': 'on'
        }
        response = self.client.post(reverse('organisations:organisation_create'), data=data)
        self.assertEqual(response.status_code, 302)
        
        # check center attributes
        organisation = Organisation.objects.get(name="New Center")
        self.assertEqual(organisation.country, country)
        self.assertIsNotNone(organisation.uuid)
