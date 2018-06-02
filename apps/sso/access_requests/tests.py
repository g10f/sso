import os

from django.conf import settings
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
