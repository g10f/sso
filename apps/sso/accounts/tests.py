from django.utils.six.moves.urllib.parse import urlsplit
import re

from django.test import override_settings
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from sso.tests import SSOSeleniumTests 
from sso.accounts.models import ApplicationRole, UserEmail
from sso.organisations.models import AdminRegion, Organisation


class AccountsSeleniumTests(SSOSeleniumTests):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']
    
    def login_test(self, username, password, test_success=True):
        self.login(username=username, password=password)
        if test_success:
            self.selenium.find_element_by_xpath('//a[@href="%s"]' % reverse('accounts:logout'))
        else:
            self.selenium.find_element_by_xpath('//form[@id="login-form"]')

    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertEqual(len(outbox), 1)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[0].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlsplit(urls[0])  # @UnusedVariable
        return path
        
    def set_reset_password(self, path, new_password):
        self.selenium.get('%s%s' % (self.live_server_url, path))
        self.selenium.find_element_by_name("new_password1").send_keys(new_password)
        self.selenium.find_element_by_name("new_password2").send_keys(new_password)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

    def set_create_password(self, path, new_password):
        self.selenium.get('%s%s' % (self.live_server_url, path))
        self.selenium.find_element_by_name("new_password1").send_keys(new_password)
        self.selenium.find_element_by_name("new_password2").send_keys(new_password)
        self.selenium.find_element_by_id("id_picture").send_keys("/usr/share/icons/gnome/32x32/emotes/face-angel.png")
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

    def test_login(self):
        # username = 'GunnarScherf'
        # password = 'gsf'
        username = 'GlobalAdmin'
        password = 'secret007'
        self.login_test(username, password)

    def test_admin_add_usermail(self):
        self.login(username='CenterAdmin', password='gsf')
        new_email = "test@g10f.de"

        # add new email
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})))
        # click tab user mails
        self.selenium.find_element_by_xpath('//a[@href="#useremail_set"]').click()
        # enter new email address
        email_element = self.selenium.find_element_by_name("useremail_set-0-email")
        email_element.clear()
        email_element.send_keys(new_email)
        self.selenium.find_element_by_xpath('//button[@name="_continue"]').click()
        self.wait_page_loaded()

        self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')

        user_email = UserEmail.objects.get(email=new_email)
        # check that the changed Email has status not confirmed
        # self.assertEqual(user_email.confirmed, False)
        # check that the changed Email has still status primary
        self.assertEqual(user_email.primary, True)
        # check that login with new_mail is possible
        self.login_test(username='test@g10f.de', password='gsf')

    @override_settings(SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES=-1)  # immediate timeout
    def test_self_failing_confirmation(self):
        self.login(username='GunnarScherf', password='gsf')
        new_email = "test@g10f.de"

        # add new email
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:emails')))
        self.selenium.find_element_by_name("email").send_keys(new_email)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

        self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')

        # try to confirm email
        confirmation_url = self.get_url_path_from_mail()
        self.selenium.get('%s%s' % (self.live_server_url, confirmation_url))
        self.wait_page_loaded()
        # we should find an error
        self.selenium.find_element_by_xpath('//div[@class="alert alert-error"]')

    def test_self_add_useremail(self):
        self.login(username='GunnarScherf', password='gsf')
        new_email = "test@g10f.de"

        # add new email
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:emails')))
        self.selenium.find_element_by_name("email").send_keys(new_email)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

        self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')

        # check that login with new email is not possible (because there is another primary email and the
        # new email is not confirmed
        self.logout()
        self.login_test(username='test@g10f.de', password='gsf', test_success=False)

        # login with existing primary email
        self.login(username='gunnar@g10f.de', password='gsf')

        # confirm email
        confirmation_url = self.get_url_path_from_mail()
        self.selenium.get('%s%s' % (self.live_server_url, confirmation_url))
        self.wait_page_loaded()
        response = self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')
        self.assertIn(new_email, response.text)

        # check that login with new_mail and old email is possible
        self.logout()
        self.login_test(username='test@g10f.de', password='gsf')
        self.logout()
        self.login_test(username='gunnar@g10f.de', password='gsf')

        # set email as primary
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:emails')))
        self.selenium.find_element_by_xpath('//button[@name="set_primary"]').click()
        response = self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')
        self.assertIn(new_email, response.text)

        # delete email
        self.selenium.find_element_by_xpath('//button[@name="delete"]').click()
        self.wait_page_loaded()
        response = self.selenium.find_element_by_xpath('//div[@class="alert alert-success"]')
        self.assertIn("gunnar@g10f.de", response.text)

    def test_delete_user(self):
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:delete_profile')))
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        self.selenium.find_element_by_xpath('//a[@href="%s"]' % reverse('auth:login'))
        
        # check if login is denied
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.find_element_by_xpath('//form/div[@class="alert alert-danger"]')  # there should be a form error
        # there should be no logout link, because user is not logged in
        self.assertEqual(len(self.selenium.find_elements_by_xpath('//ul/li/a[@href="%s"]' % reverse('accounts:logout'))), 0)

    def test_change_password(self):
        username = 'GlobalAdmin'
        old_password = 'secret007'
        new_password = 'gsf1zgh'

        self.login_test(username, old_password)
        
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:password_change')))
        self.selenium.find_element_by_name("old_password").send_keys(old_password)
        self.selenium.find_element_by_name("new_password1").send_keys(new_password)
        self.selenium.find_element_by_name("new_password2").send_keys(new_password)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

        self.logout()

        self.login_test(username, new_password)

    def test_password_reset(self):
        username = 'gunnar@g10f.de'
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:password_reset')))
        self.selenium.find_element_by_name("email").send_keys('gunnar@g10f.de')
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        
        self.assertEqual(len(self.selenium.find_elements_by_class_name("alert-error")), 0)
        
        path = self.get_url_path_from_mail()
        
        new_password = 'gsf1zghxyz'
        self.set_reset_password(path, new_password)
        self.login_test(username, new_password)

    def test_change_profile_success(self):
        new_first_name = 'Test'
        new_last_name = 'User'
        new_email = 'mail@g10f.de'
        
        self.login(username='GunnarScherf', password='gsf')

        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:profile')))
        
        first_name = self.selenium.find_element_by_name("first_name")
        first_name.clear()
        first_name.send_keys(new_first_name)
        
        last_name = self.selenium.find_element_by_name("last_name")
        last_name.clear()
        last_name.send_keys(new_last_name)
        
        # email = self.selenium.find_element_by_name("email")
        # email.clear()
        # email.send_keys(new_email)

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        
        first_name = self.selenium.find_element_by_name("first_name")
        self.assertEqual(first_name.get_attribute("value"), new_first_name)

        last_name = self.selenium.find_element_by_name("last_name")
        self.assertEqual(last_name.get_attribute("value"), new_last_name)

        # email = self.selenium.find_element_by_name("email")
        # self.assertEqual(email.get_attribute("value"), new_email)

    def test_change_profile_failure(self):
        new_homepage = 'http:/home'  # wrong url format
        
        self.login(username='GunnarScherf', password='gsf')
        
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:profile')))
                
        homepage = self.selenium.find_element_by_name("homepage")
        homepage.clear()
        homepage.send_keys(new_homepage)

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

        self.assertEqual(len(self.selenium.find_elements_by_class_name("alert-danger")), 1)

    def test_add_user_as_admin(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Admin")
        allowed_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0745', '31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs)
    
    def test_add_user_as_region(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Region")
        region = AdminRegion.objects.get_by_natural_key('0ebf2537fc664b7db285ea773c981404')
        allowed_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0745', '31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs, region=region)

    def test_add_user_as_center(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Center")
        allowed_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0745'])
        denied_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs, denied_orgs=denied_orgs)
    
    def add_user(self, applicationrole, allowed_orgs, denied_orgs=None, region=None):
        if denied_orgs is None:
            denied_orgs = []
        
        user = get_user_model().objects.get(username='GunnarScherf')
        user.application_roles.add(applicationrole)
        if region:
            user.admin_regions.add(region)
        
        # login as admin and add new user
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:add_user')))
        self.wait_page_loaded()

        new_first_name = 'Test'
        new_last_name = 'User'
        new_email = 'mail@g10f.de'
        new_gender = 'm'

        first_name = self.selenium.find_element_by_name("first_name")
        first_name.send_keys(new_first_name)
        
        last_name = self.selenium.find_element_by_name("last_name")
        last_name.send_keys(new_last_name)
        
        email = self.selenium.find_element_by_name("email")
        email.send_keys(new_email)

        gender = self.selenium.find_element_by_name("gender")
        gender.send_keys(new_gender)

        organisation = Select(self.selenium.find_element_by_name("organisation"))
        
        # test error case
        for org in denied_orgs:
            try:
                organisation.select_by_value(str(org.pk))
                raise Exception("Organisation with pk=%s should not be a possible option" % org)
            except NoSuchElementException:
                pass                
        
        for org in allowed_orgs:
            organisation.select_by_value(str(org.pk))            

        self.selenium.find_element_by_xpath('//a[@href="#app_roles"]').click()
        self.selenium.find_element_by_id("id_application_roles_1").click()

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        self.assertEqual(len(self.selenium.find_elements_by_class_name("alert-success")), 1)
        
        # get the password reset link from the email to the new user
        # and set a new password
        path = self.get_url_path_from_mail()
        
        new_password = 'gsf1zghxyz'
        self.set_create_password(path, new_password)
        
        # login as new user with the new password
        self.login_test(new_email, new_password)

        # check if we have the Test App in the app roles
        self.selenium.find_element_by_xpath('//a[@href="http://test.example.com"]')
