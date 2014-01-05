# -*- coding: utf-8 -*-
import urlparse
import re

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from sso.tests import SSOSeleniumTests 
from sso.accounts.models import ApplicationRole

class AccountsSeleniumTests(SSOSeleniumTests):
    fixtures = ['initial_data.json', 'app_roles.json', 'test_user_data.json']
    
    def login_test(self, username, password):
        self.login(username=username, password=password)
        self.selenium.find_element_by_xpath('//a[@href="%s"]' % reverse('accounts:logout'))        
        
    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertEqual(len(outbox), 1)
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', outbox[0].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlparse.urlsplit(urls[0])  # @UnusedVariable
        return path
        
    def set_reset_password(self, path, new_password):
        self.selenium.get('%s%s' % (self.live_server_url, path))
        self.selenium.find_element_by_name("new_password1").send_keys(new_password)
        self.selenium.find_element_by_name("new_password2").send_keys(new_password)
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        
    def test_login(self):
        #username = 'GunnarScherf'
        #password = 'gsf'
        username = 'GlobalAdmin'
        password = 'secret007'
        self.login_test(username, password)
        
    def test_delete_user(self):
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:delete_profile')))
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        self.selenium.find_element_by_xpath('//a[@href="%s"]' % reverse('accounts:login'))
        
        # check if login is denied
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.find_element_by_xpath('//form/div[@class="alert alert-danger"]')  # there should be a form error
        # there should be no logout link, because user is not logged in
        self.assertEqual(len(self.selenium.find_elements_by_xpath('//a[@href="%s"]' % reverse('accounts:logout'))), 0)  

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
        
        self.selenium.find_element_by_xpath('//a[@href="%s"]' % reverse('accounts:logout')).click()        
        self.wait_page_loaded()   
        
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
        
        email = self.selenium.find_element_by_name("email")
        email.clear()
        email.send_keys(new_email)

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        
        first_name = self.selenium.find_element_by_name("first_name")
        self.assertEqual(first_name.get_attribute("value"), new_first_name)

        last_name = self.selenium.find_element_by_name("last_name")
        self.assertEqual(last_name.get_attribute("value"), new_last_name)

        email = self.selenium.find_element_by_name("email")
        self.assertEqual(email.get_attribute("value"), new_email)

    def test_change_profile_failure(self):
        new_email = 'admin@g10f.de'
        
        self.login(username='GunnarScherf', password='gsf')
        
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:profile')))
                
        email = self.selenium.find_element_by_name("email")
        email.clear()
        email.send_keys(new_email)

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()

        self.assertEqual(len(self.selenium.find_elements_by_class_name("alert-danger")), 1)

    def test_add_user_as_admin(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name="Admin")
        self.add_user(applicationrole=applicationrole, allowed_orgs=["1", "2"])
    
    def test_add_user_as_region(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name="Region")
        self.add_user(applicationrole=applicationrole, allowed_orgs=["1", "2"])

    def test_add_user_as_center(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.APP_UUID, role__name="Center")
        self.add_user(applicationrole=applicationrole, allowed_orgs=["1"], denied_orgs=["2"])
    
    def add_user(self, applicationrole, allowed_orgs, denied_orgs=[]):
        
        user = get_user_model().objects.get(username='GunnarScherf')
        user.application_roles.add(applicationrole)
        user.save()
        
        # login as admin and add new user
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:add_user')))

        new_first_name = 'Test'
        new_last_name = 'User'
        new_email = 'mail@g10f.de'

        first_name = self.selenium.find_element_by_name("first_name")
        first_name.send_keys(new_first_name)
        
        last_name = self.selenium.find_element_by_name("last_name")
        last_name.send_keys(new_last_name)
        
        email = self.selenium.find_element_by_name("email")
        email.send_keys(new_email)

        organisation = Select(self.selenium.find_element_by_name("organisation"))
        
        # test error case
        for org in denied_orgs:
            try:
                organisation.select_by_value(org)
                raise Exception("Organisation with pk=%s should not be a possible option" % org)
            except NoSuchElementException:
                pass                
        
        for org in allowed_orgs:
            organisation.select_by_value(org)            

        self.selenium.find_element_by_xpath('//a[@href="#app_roles"]').click()
        self.selenium.find_element_by_id("id_application_roles_1").click()

        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()
        self.wait_page_loaded()
        self.assertEqual(len(self.selenium.find_elements_by_class_name("alert-success")), 1)
        
        # get the password reset link from the email to the new user
        # and set a new password
        path = self.get_url_path_from_mail()
        
        new_password = 'gsf1zghxyz'
        self.set_reset_password(path, new_password)
        
        # login as new user with the new password
        self.login_test(new_email, new_password)

        # check if we have the Test App in the app roles
        self.selenium.find_element_by_xpath('//a[@href="http://test.example.com"]')
