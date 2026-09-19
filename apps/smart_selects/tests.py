from django.http import Http404
from django.test import TestCase, RequestFactory
from django.urls import reverse
from smart_selects.views import filterchain
from sso.organisations.models import OrganisationCountry, AdminRegion


class FilterChainTest(TestCase):
    fixtures = ['test_l10n_data.json', 'test_organisation_data.json']

    def test_allowed_chains(self):
        organisation_country = OrganisationCountry.active_objects.first()
        url = reverse('chained_filter', kwargs={'field': 'association', 'value': organisation_country.association_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(organisation_country.pk, [item['value'] for item in response.json()])

        admin_region = AdminRegion.active_objects.first()
        url = reverse('chained_filter',
                      kwargs={'field': 'organisation_country', 'value': admin_region.organisation_country_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(admin_region.pk, [item['value'] for item in response.json()])

    def test_not_allowed_field_in_url(self):
        # lookups across relations must not be possible, otherwise the response is an oracle for secret values
        for model in ['OrganisationCountry', 'AdminRegion']:
            for field in ['organisation__user__password__startswith',
                          'organisation__user__device__totpdevice__key__startswith',
                          'association__organisationcountry__organisation__user__bearertoken__refresh_token__token__startswith',
                          'uuid']:
                response = self.client.get(f'/chained_filter/organisations/{model}/{field}/a/')
                self.assertEqual(response.status_code, 404, f'{model} {field}')

    def test_not_allowed_value_in_url(self):
        response = self.client.get('/chained_filter/organisations/OrganisationCountry/association/abc/')
        self.assertEqual(response.status_code, 404)

    def test_not_allowed_field_in_view(self):
        request = RequestFactory().get('/')
        with self.assertRaises(Http404):
            filterchain(request, app='organisations', model='AdminRegion', field='organisation__user__password__startswith',
                        value='1', manager='active_objects')
        with self.assertRaises(Http404):
            filterchain(request, app='accounts', model='User', field='association', value='1')
        with self.assertRaises(Http404):
            filterchain(request, app='organisations', model='AdminRegion', field='organisation_country', value='1a',
                        manager='active_objects')
