from django.conf import settings
from django.test import TransactionTestCase
from django.urls import reverse
from sso.organisations.forms import OrganisationEmailAdminForm
from sso.organisations.models import OrganisationCountry, Organisation, AdminRegion
from sso.test.client import SSOClient


class OrganisationsTest(TransactionTestCase):
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
        organisation_country = OrganisationCountry.objects.get(uuid='6bc429702f9f442ea9717824a8d76d84')
        countries = response.context['form'].fields['organisation_country'].queryset
        self.assertEqual(len(countries), 1)
        self.assertEqual(organisation_country, countries[0])
        email_domain = settings.SSO_ORGANISATION_EMAIL_DOMAIN if settings.SSO_ORGANISATION_EMAIL_DOMAIN else '@g10f.de'

        # create a new center
        data = {
            'name': 'New Center',
            'center_type': 'g',
            'organisation_country': organisation_country.pk,
            'email_value': 'newcenter' + email_domain,
            'email_forward': 'test@g10f.de',
            'is_active': 'on'
        }
        response = self.client.post(reverse('organisations:organisation_create'), data=data)
        self.assertEqual(response.status_code, 302)

        # check center attributes
        organisation = Organisation.objects.get(name="New Center")
        self.assertEqual(organisation.organisation_country, organisation_country)
        self.assertIsNotNone(organisation.uuid)

    def test_add_organisation_by_region_admin(self):
        self.client.login(username='RegionAdmin', password='gsf')
        response = self.client.get(reverse('organisations:organisation_create'))

        self.assertEqual(response.status_code, 200)
        # RegionAdmin is admin of Region 0ebf2537fc664b7db285ea773c981404
        organisation_country = OrganisationCountry.objects.get(uuid='6bc429702f9f442ea9717824a8d76d84')
        countries = response.context['form'].fields['organisation_country'].queryset
        self.assertEqual(len(countries), 1)
        self.assertEqual(organisation_country, countries[0])
        email_domain = settings.SSO_ORGANISATION_EMAIL_DOMAIN if settings.SSO_ORGANISATION_EMAIL_DOMAIN else '@g10f.de'

        admin_region = AdminRegion.objects.get(uuid='0ebf2537fc664b7db285ea773c981404')

        # create a new center
        data = {
            'name': 'New Center',
            'center_type': 'g',
            'organisation_country': organisation_country.pk,
            'admin_region': admin_region.pk,
            'email_value': 'newcenter' + email_domain,
            'email_forward': 'test@g10f.de',
            'is_active': 'on'
        }
        response = self.client.post(reverse('organisations:organisation_create'), data=data)
        self.assertEqual(response.status_code, 302)

        # check center attributes
        organisation = Organisation.objects.get(name="New Center")
        self.assertEqual(organisation.organisation_country, organisation_country)
        self.assertIsNotNone(organisation.uuid)

        # create a new center with existing email from region
        data = {
            'name': 'New Center2',
            'center_type': 'g',
            'organisation_country': organisation_country.pk,
            'admin_region': admin_region.pk,
            'email_value': 'newcenter' + email_domain,
            'email_forward': 'test@g10f.de',
            'is_active': 'on'
        }
        response = self.client.post(reverse('organisations:organisation_create'), data=data)
        self.assertEqual(response.status_code, 200)
        error_msg = OrganisationEmailAdminForm.error_messages['email_already_exists']
        self.assertFormError(response.context['form'], 'email_value', [error_msg])

    def test_some_list(self):
        self.client.login(username='CountryAdmin', password='gsf')

        response = self.client.get(reverse('organisations:adminregion_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('organisations:adminregion_list'), data={'country': OrganisationCountry.objects.first().pk})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('organisations:adminregion_list'), data={'country': 99999})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('organisations:organisation_list_txt'))
        self.assertEqual(response.status_code, 200)
