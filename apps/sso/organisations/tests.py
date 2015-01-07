# -*- coding: utf-8 -*-
import urlparse
import re
from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from sso.organisations.models import OrganisationCountry, Organisation
from sso.accounts.models import User


class OrganisationssTest(TestCase):
    fixtures = ['roles.json', 'app_roles.json', 'test_l10n_data.xml', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']

    def setUp(self):
        self.client = Client()
    
    def tearDown(self):
        pass
    
    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertEqual(len(outbox), 1)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[0].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlparse.urlsplit(urls[0])  # @UnusedVariable
        return path

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
            'email_value': 'newcenter@diamondway-center.org',
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
        
        # check that a new center account was created
        user = User.objects.get_by_email('newcenter@diamondway-center.org')
        self.assertTrue(user.is_center)
        
        self.assertIn(organisation, user.organisations.all())

        # check admin profile of center account
        default_admin_profile = User.get_default_admin_profile()        
        self.assertIn(default_admin_profile, user.role_profiles.all())
        
        # check if the center account can edit the center
        # first reset the password because the account was just created and has a random password
        # then login with the new password and try changing the center data
        response = self.client.post(reverse('accounts:password_reset'), 
                                    data={'email': 'newcenter@diamondway-center.org'})
        self.assertEqual(response.status_code, 302)
        
        new_password = 'gsf1zghxyz'
        path = self.get_url_path_from_mail()
        response = self.client.post(path, 
                                    data={'new_password1': new_password, 'new_password2': new_password})
        self.assertEqual(response.status_code, 302)
        self.client.login(username='newcenter@diamondway-center.org', password=new_password)
        # update center
        org_id = organisation.pk
        email_id = organisation.email.pk
        data = {
            'coordinates_type': 3,
            'emailforward_set-0-email': email_id,
            'emailforward_set-0-forward': 'gunnar@g10f.de',
            'emailforward_set-0-id': '',
            'emailforward_set-INITIAL_FORMS': 0,
            'emailforward_set-MAX_NUM_FORMS': 10,
            'emailforward_set-MIN_NUM_FORMS': 0,
            'emailforward_set-TOTAL_FORMS': 1,
            'founded_day': 23,
            'founded_month': 10,
            'founded_year': 2014,
            'homepage': 'http://newcenter.de/',
            'location': 'SRID=3857;POINT(1286998.028908273 6131762.443410875)',
            'organisationaddress_set-0-address_type': 'meditation',
            'organisationaddress_set-0-addressee': 'Buddhistisches Zentrum New',
            'organisationaddress_set-0-city': 'München',
            'organisationaddress_set-0-country': 81,
            'organisationaddress_set-0-id': '',
            'organisationaddress_set-0-organisation': org_id,
            'organisationaddress_set-0-postal_code': 38122,
            'organisationaddress_set-0-region': '',
            'organisationaddress_set-0-street_address': 'Kramerstr. 19a',
            'organisationaddress_set-INITIAL_FORMS': 0,
            'organisationaddress_set-MAX_NUM_FORMS': 2,
            'organisationaddress_set-MIN_NUM_FORMS': 0,
            'organisationaddress_set-TOTAL_FORMS': 1,
            'organisationphonenumber_set-0-id': '',
            'organisationphonenumber_set-0-organisation': org_id,
            'organisationphonenumber_set-0-phone': '+49 (0531) ...',
            'organisationphonenumber_set-0-phone_type': 'home',
            'organisationphonenumber_set-INITIAL_FORMS': 0,
            'organisationphonenumber_set-MAX_NUM_FORMS': 6,
            'organisationphonenumber_set-MIN_NUM_FORMS': 0,
            'organisationphonenumber_set-TOTAL_FORMS': 1,
        }
        response = self.client.post(reverse('organisations:organisation_update', args=[organisation.uuid]), data=data)
        self.assertEqual(response.status_code, 302)
        
        # request the new data
        response = self.client.get(reverse('organisations:organisation_detail', args=[organisation.uuid]))
        self.assertEqual(response.status_code, 200)
        obj = response.context['object']
        self.assertEqual(obj.organisationaddress_set.all()[0].addressee, 'Buddhistisches Zentrum New')
        self.assertEqual(obj.organisationphonenumber_set.all()[0].phone, '+49 (0531) ...')
        self.assertEqual(obj.email.emailforward_set.all()[0].forward, 'gunnar@g10f.de')
