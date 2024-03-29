import os
import re
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from sso.organisations.models import Organisation
from sso.registration import default_username_generator
from sso.test.client import SSOClient
from sso.tests import SSOSeleniumTests


class RegistrationSeleniumTests(SSOSeleniumTests):
    fixtures = ['roles.json', 'app_roles.json', 'test_l10n_data.json', 'test_organisation_data.json',
                'test_app_roles.json',
                'test_user_data.json']

    @override_settings(SSO_RECAPTCHA_ENABLED=False)
    def test_registration(self):
        organisation = Organisation.objects.filter(is_active=True).first()
        self.selenium.get('%s%s' % (
            self.live_server_url, reverse('registration:registration_register')))
        self.wait_page_loaded()
        self.selenium.find_element(by=By.NAME, value="email").send_keys('test2@g10f.de')
        self.selenium.find_element(by=By.NAME, value="first_name").send_keys('first_name')
        self.selenium.find_element(by=By.NAME, value="last_name").send_keys('last_name')
        self.selenium.find_element(by=By.NAME, value="known_person1_first_name").send_keys('known_person1_first_name')
        self.selenium.find_element(by=By.NAME, value="known_person2_first_name").send_keys('known_person2_first_name')
        self.selenium.find_element(by=By.NAME, value="known_person1_last_name").send_keys('known_person1_last_name')
        self.selenium.find_element(by=By.NAME, value="known_person2_last_name").send_keys('known_person2_last_name')
        self.selenium.find_element(by=By.NAME, value="city").send_keys('The City')
        picture = os.path.abspath(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'))
        self.add_picture(picture)

        country_select = Select(self.selenium.find_element(by=By.NAME, value="country"))
        country_select.select_by_value('81')
        organisation_select = Select(self.selenium.find_element(by=By.NAME, value="organisation"))
        organisation_select.select_by_value(str(organisation.pk))

        for user_extra_attribute in settings.SSO_TEST_USER_EXTRA_ATTRIBUTES:
            extra_select = Select(self.selenium.find_element(by=By.NAME, value=user_extra_attribute['name']))
            extra_select.select_by_value(user_extra_attribute['value'])

        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.selenium.find_element(by=By.XPATH, value='//button[@name="_edit_again"]')


class RegistrationTest(TestCase):
    fixtures = ['roles.json', 'app_roles.json', 'test_l10n_data.json', 'test_organisation_data.json',
                'test_app_roles.json',
                'test_user_data.json']

    def setUp(self):
        os.environ['RECAPTCHA_TESTING'] = 'True'
        self.client = SSOClient()

    def tearDown(self):
        del os.environ['RECAPTCHA_TESTING']

    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertGreater(len(outbox), 0)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                          outbox[-1].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlsplit(urls[0])  # @UnusedVariable
        return path

    def test_default_username_generator(self):
        username = default_username_generator("Gunnar", "Scherf")
        self.assertEqual(username, "GunnarScherf1")

        username = default_username_generator("Hans", "Meier")
        self.assertEqual(username, "HansMeier")

        username = default_username_generator("1234567890", "12345678901234567890123456789012345678901234567890"
                                                            "1234567890")
        self.assertEqual(username, "123456789012345678901234567890123456789012345678901234567890123456789")

    @override_settings(RECAPTCHA_PUBLIC_KEY='6LccjewSAAAAAPcFZmUtuzRVkU6hhOona0orqgKh',
                       RECAPTCHA_PRIVATE_KEY='6LccjewSAAAAAAhJzHuEyVV40AYApL6CpmjqlmX8',
                       SSO_RECAPTCHA_ENABLED=True)
    def test_registration_register_by_bot(self):
        """
        User self registration with email validation
        """
        data = {
            'email': 'test2@g10f.de',
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
        self.assertFormError(response.context['form'], 'captcha', ['Error verifying reCAPTCHA, please try again.'])

    @override_settings(SSO_RECAPTCHA_ENABLED=True)
    def test_registration(self):
        """
        User self registration with email validation
        """
        response = self.client.get(reverse('registration:registration_register'))
        self.assertEqual(response.status_code, 200)
        organisation = Organisation.objects.filter(is_active=True).first()

        data = {
            'email': 'test2@g10f.de',
            'picture':
                "data:image/jpeg;base64,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",
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
        for user_extra_attribute in settings.SSO_TEST_USER_EXTRA_ATTRIBUTES:
            data[user_extra_attribute['name']] = user_extra_attribute['value']

        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertNotContains(response, 'is-invalid')

        # captcha is only displayed once.
        # the second time a signed value is used
        del data['g-recaptcha-response']
        data['state'] = response.context['form'].data['state']

        data[response.context['stage_field']] = "2"
        data[response.context['hash_field']] = response.context['hash_value']

        response = self.client.post(reverse('registration:registration_register'), data=data)
        self.assertEqual(response.status_code, 302)

        path = self.get_url_path_from_mail()
        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)

        response = self.client.get(response['Location'])
        self.assertEqual(response.status_code, 200)

    def test_registration_list(self):
        # admin logs in
        self.client.login(username='GlobalAdmin', password='secret007')
        response = self.client.get(reverse('registration:user_registration_list'))
        self.assertEqual(response.status_code, 200)
