import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from sso.organisations.models import Organisation
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
        self.add_picture(picture)

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
        elems = self.selenium.find_elements(by=By.XPATH, value="//a[starts-with(@href, '%s')]" % list_url)
        # should be one element in the list
        elems[0].click()
        self.wait_page_loaded()
        self.selenium.find_element_by_tag_name("form").submit()
        # check success message
        self.wait_page_loaded()
        self.selenium.find_element_by_class_name("alert-success")
        self.logout()

        # check if the user got the member profile
        user = get_user_model().objects.get(username='GunnarScherf')
        self.assertIn(get_user_model().get_default_role_profile(), user.role_profiles.all())
        self.assertNotIn(get_user_model().get_default_guest_profile(), user.role_profiles.all())

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
        self.add_picture(picture)
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
        elems = self.selenium.find_elements(by=By.XPATH, value="//a[starts-with(@href, '%s')]" % list_url)
        # should be one element in the list
        elems[0].click()
        self.wait_page_loaded()
        self.selenium.find_element_by_tag_name("form").submit()
        # check success message
        self.wait_page_loaded()
        self.selenium.find_element_by_class_name("alert-success")
        self.logout()

        user.refresh_from_db()
        organisation = Organisation.objects.get(uuid='31664dd38ca4454e916e55fe8b1f0745')
        self.assertIn(organisation, user.organisations.all())
        self.assertEqual(len(user.organisations.all()), 1)
        self.assertIn(get_user_model().get_default_role_profile(), user.role_profiles.all())
        self.assertNotIn(get_user_model().get_default_guest_profile(), user.role_profiles.all())
