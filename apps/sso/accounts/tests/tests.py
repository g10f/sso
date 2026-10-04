from django.urls import reverse
from django.test import TestCase
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
