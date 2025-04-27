from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from django.urls import reverse
from sso.oauth2.models import Client
from sso.tests import SSOSeleniumTests


class AppSelfServiceSeleniumTests(SSOSeleniumTests):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json',
                'test_app_roles.json', 'test_user_data.json', 'test_user_attributes.json']

    def test_add_application(self):
        browser = self.selenium

        # add a new app with an app admin
        app_name = "The Killer App"
        self.login(username='GlobalAdmin', password='secret007')
        browser.get(f"{self.live_server_url}{reverse('accounts:application_add')}")
        browser.find_element(by=By.NAME, value="title").send_keys(app_name)
        browser.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()
        browser.find_element(by=By.CSS_SELECTOR, value="a[rel='update']").click()
        browser.find_element(by=By.CSS_SELECTOR, value="a[href='#applicationadmin_set']").click()
        browser.find_element(by=By.NAME, value="applicationadmin_set-1-admin_email").send_keys("app-admin@g10f.de")
        browser.find_element(by=By.TAG_NAME, value="form").submit()

        # add client with access to all users
        browser.find_element(by=By.CSS_SELECTOR, value="a[rel='add-client']").click()
        browser.find_element(by=By.NAME, value="name").send_keys("my-secret-client")
        Select(browser.find_element(by=By.NAME, value="type")).select_by_value("service")
        browser.find_element(by=By.NAME, value="can_access_all_users").click()
        browser.find_element(by=By.TAG_NAME, value="form").submit()
        browser.find_element(by=By.CLASS_NAME, value="alert-success")
        client_update_uri = browser.find_element(by=By.CSS_SELECTOR, value="a[rel='update-client']").get_attribute("href")
        self.logout()

        # open app list and navigate to app
        self.login(username='ApplicationAdmin', password='gsf')

        # check that user has no access to the OIDC client with "access to all users"
        browser.get(client_update_uri)
        self.assertIn("Sorry, but you have no permission for the page you were trying to view.", browser.page_source)

        browser.get(f"{self.live_server_url}{reverse('accounts:application_list')}")
        self.wait_page_loaded()

        browser.find_element(by=By.LINK_TEXT, value=app_name).click()

        # add confidential client
        browser.find_element(by=By.CSS_SELECTOR, value="a[rel='add-client']").click()
        browser.find_element(by=By.NAME, value="name").send_keys("my-client")
        browser.find_element(by=By.NAME, value="redirect_uris").send_keys("https://example.com")
        browser.find_element(by=By.TAG_NAME, value="form").submit()
        browser.find_element(by=By.CLASS_NAME, value="alert-success")

        # add service account
        service_account_client_name = "my-service-client"
        browser.find_element(by=By.CSS_SELECTOR, value="a[rel='add-client']").click()
        browser.find_element(by=By.NAME, value="name").send_keys(service_account_client_name)
        Select(browser.find_element(by=By.NAME, value="type")).select_by_value("service")
        with self.assertRaises(NoSuchElementException):
            # ensure can_access_all_users is not available unless user has access to all users
            browser.find_element(by=By.NAME, value="can_access_all_users")
        browser.find_element(by=By.TAG_NAME, value="form").submit()
        browser.find_element(by=By.CLASS_NAME, value="alert-success")

        client = Client.objects.get(name=service_account_client_name, application__title=app_name)
        self.assertFalse(client.has_access_to_all_users)
