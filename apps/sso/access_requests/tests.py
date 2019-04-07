import os

from selenium.webdriver.support.select import Select

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from sso.tests import SSOSeleniumTests


class AccessRequestsSeleniumTests(SSOSeleniumTests):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json',
                'test_app_roles.json', 'test_user_data.json']

    def test_new_access_request(self):
        self.login(username='GunnarScherf', password='gsf')

        # add new access request
        self.selenium.get('%s%s' % (self.live_server_url, reverse('access_requests:extend_access')))
        self.selenium.find_element_by_name("message").send_keys('Hello world.')

        picture = os.path.abspath(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'))
        self.selenium.find_element_by_name("_dummy").send_keys(picture)

        self.selenium.find_element_by_tag_name("form").submit()

        self.wait_page_loaded()

        url = reverse('access_requests:extend_access_thanks')
        full_url = self.live_server_url + url
        self.assertEqual(self.selenium.current_url, full_url)

    def test_new_access_request_for_user_without_organisation(self):
        # remove all organisations from user
        user = get_user_model().objects.get(username='GunnarScherf')
        user.organisations.clear()

        self.login(username='GunnarScherf', password='gsf')

        # add new access request
        self.selenium.get('%s%s?app_id=%s' % (self.live_server_url, reverse('access_requests:extend_access'),
                                              'bc0ee635a536491eb8e7fbe5749e8111'))
        self.selenium.find_element_by_name("message").send_keys('Hello world.')
        picture = os.path.abspath(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'))
        self.selenium.find_element_by_name("_dummy").send_keys(picture)
        Select(self.selenium.find_element_by_name("organisation")).select_by_index(1)
        self.selenium.find_element_by_tag_name("form").submit()
        self.wait_page_loaded()

        url = reverse('access_requests:extend_access_thanks')
        full_url = self.live_server_url + url
        self.assertEqual(self.selenium.current_url, full_url)
        self.logout()

        # login as organisation admin and accept the request
        self.login(username='CenterAdmin', password='gsf')

        list_url = reverse('access_requests:extend_access_list')
        self.selenium.get('%s%s' % (self.live_server_url, list_url))
        elems = self.selenium.find_elements_by_xpath("//a[starts-with(@href, '%s')]" % list_url)
        # should be one element in the list
        elems[0].click()
        self.wait_page_loaded()
        self.selenium.find_element_by_tag_name("form").submit()

        # check success message
        self.wait_page_loaded()
        self.selenium.find_element_by_class_name("alert-success")
        self.logout()
