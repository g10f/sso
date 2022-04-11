from selenium.webdriver.common.by import By

from django.urls import reverse
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
        self.logout()

        # add confidential client
        self.login(username='ApplicationAdmin', password='gsf')
        browser.get(f"{self.live_server_url}{reverse('accounts:application_list')}")
        browser.find_element(by=By.LINK_TEXT, value=app_name).click()
        browser.find_element(by=By.CSS_SELECTOR, value="a[rel='add-client']").click()
        browser.find_element(by=By.NAME, value="name").send_keys("my-client")
        browser.find_element(by=By.NAME, value="redirect_uris").send_keys("https://example.com")
        browser.find_element(by=By.TAG_NAME, value="form").submit()
        browser.find_element(by=By.CLASS_NAME, value="alert-success")


