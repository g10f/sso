import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, override_settings
from django.utils.timezone import now
from sso.accounts.models import OrganisationChange
from sso.organisations.models import Organisation, OrganisationCountry
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

    def test_user_list_filters_cache_key_is_stable_across_processes(self):
        # hash() of a str differs per process, so the {% cache %} key must not be built with it
        result = self.client.login(username='GlobalAdmin', password='secret007')
        self.assertEqual(result, True)

        response = self.client.get(reverse('accounts:user_list'), data={'q': 'admin'})
        self.assertEqual(response.status_code, 200)

        filters_cache_key = response.context['filters_cache_key']
        self.assertIsInstance(filters_cache_key, str)
        self.assertEqual(json.loads(filters_cache_key)['q'], 'admin')

    def test_app_admin_update_user(self):
        result = self.client.login(username='ApplicationAdmin', password='gsf')
        self.assertEqual(result, True)

        # User.objects.get()
        response = self.client.get(reverse('accounts:app_admin_user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('accounts:app_admin_update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'}))

        response = self.client.get(reverse('accounts:app_admin_update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'}))
        self.assertEqual(response.status_code, 200)


@override_settings(SSO_VALIDATION_PERIOD_IS_ACTIVE=True, SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL=True)
class OrganisationChangeValidityTest(TestCase):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']

    def setUp(self):
        self.user = get_user_model().objects.get(username='CenterAdmin')
        self.admin = get_user_model().objects.get(username='GlobalAdmin')
        self.organisation = Organisation.objects.exclude(pk__in=self.user.organisations.all()).first()

    def _verify_change(self, valid_until):
        self.user.valid_until = valid_until
        self.user.save()
        organisation_change = OrganisationChange.objects.create(user=self.user, organisation=self.organisation)
        organisation_change.verify(self.admin)
        self.user.refresh_from_db()

    def test_accepted_organisation_change_restarts_validity(self):
        self._verify_change(now() + timedelta(days=14))
        expected = now() + timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        self.assertAlmostEqual(self.user.valid_until, expected, delta=timedelta(minutes=1))

    def test_accepted_organisation_change_does_not_shorten_validity(self):
        valid_until = now() + timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS + 100)
        self._verify_change(valid_until)
        self.assertEqual(self.user.valid_until, valid_until)


class AdminMailLogLevelTests(TestCase):
    """Regression: operational/data conditions must be logged at warning, not
    error, so they do not trigger an admin email per occurrence."""

    def test_email_user_without_primary_email_logs_warning(self):
        from django.contrib.auth import get_user_model
        import logging
        User = get_user_model()
        user = User.objects.create_user(username='noemail')
        logger_name = 'sso.accounts.models.user'
        with self.assertLogs(logger_name, level='WARNING') as cm:
            sent = user.email_user('subject', 'body')
        self.assertEqual(sent, 0)
        recs = [r for r in cm.records if 'has no primary_email' in r.getMessage()]
        self.assertTrue(recs)
        self.assertTrue(all(r.levelno < logging.ERROR for r in recs))

    def test_password_reset_unusable_password_logs_warning(self):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory
        from django.urls import NoReverseMatch
        import logging
        from sso.accounts.forms.password import PasswordResetForm
        User = get_user_model()
        user = User.objects.create_user(username='nopw')
        user.set_unusable_password()
        user.save()
        user.create_primary_email('nopw@example.invalid', confirmed=True)
        form = PasswordResetForm(data={'email': 'nopw@example.invalid'})
        # bypass clean_email (which already rejects unusable passwords) to reach save()
        form.cleaned_data = {'email': 'nopw@example.invalid'}
        request = RequestFactory().get('/')
        logger_name = 'sso.accounts.forms.password'
        with self.assertLogs(logger_name, level='WARNING') as cm:
            # the warning is logged before the email is rendered; rendering the
            # reset email reverses 'password_reset_confirm', which is only wired
            # up by the theme urlconf, not the base test urlconf -> swallow that.
            try:
                form.save(request=request)
            except NoReverseMatch:
                pass
        recs = [r for r in cm.records if 'unusable password' in r.getMessage()]
        self.assertTrue(recs)
        self.assertTrue(all(r.levelno < logging.ERROR for r in recs))
