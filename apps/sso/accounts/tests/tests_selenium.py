import os
import re
from urllib.parse import urlencode
from urllib.parse import urlsplit

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from sso.accounts.models import ApplicationRole, UserEmail
from sso.organisations.models import AdminRegion, Organisation
from sso.tests import SSOSeleniumTests


class AccountsSeleniumTests(SSOSeleniumTests):
    fixtures = ['roles.json', 'test_l10n_data.json', 'app_roles.json', 'test_organisation_data.json',
                'test_app_roles.json', 'test_user_data.json', 'test_user_attributes.json']

    def login_test(self, username, password, test_success=True):
        self.login(username=username, password=password)
        if test_success:
            self.selenium.find_element(by=By.XPATH, value='//a[@href="%s"]' % reverse('auth:logout'))
        else:
            self.selenium.find_element(by=By.XPATH, value='//form[@id="login-form"]')

    def get_url_path_from_mail(self):
        outbox = getattr(mail, 'outbox')
        self.assertEqual(len(outbox), 1)
        urls = re.findall('https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+',
                          outbox[0].body)
        self.assertEqual(len(urls), 1)
        scheme, netloc, path, query_string, fragment = urlsplit(urls[0])  # @UnusedVariable
        return path

    def set_reset_password(self, path, new_password):
        self.selenium.get('%s%s' % (self.live_server_url, path))
        self.wait_page_loaded()
        self.selenium.find_element(by=By.NAME, value="new_password1").send_keys(new_password)
        self.selenium.find_element(by=By.NAME, value="new_password2").send_keys(new_password)
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        if settings.SSO_POST_RESET_LOGIN:
            url = reverse('home')
        else:
            url = reverse('auth:login')

        self.selenium.find_element(by=By.XPATH, value='//a[@href="%s"]' % url)

    def set_create_password(self, path, new_password):
        self.selenium.get('%s%s' % (self.live_server_url, path))
        self.selenium.find_element(by=By.NAME, value="new_password1").send_keys(new_password)
        self.selenium.find_element(by=By.NAME, value="new_password2").send_keys(new_password)
        picture = os.path.abspath(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'))
        self.add_picture(picture)
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

    def test_login(self):
        username = 'GlobalAdmin'
        password = 'secret007'
        self.login_test(username, password)

    def test_admin_add_usermail(self):
        self.login(username='CenterAdmin', password='gsf')
        new_email = "test@g10f.de"

        # add new email
        self.selenium.get('%s%s' % (
            self.live_server_url, reverse('accounts:update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})))
        # click tab user mails
        self.selenium.find_element(by=By.XPATH, value='//a[@href="#useremail_set"]').click()
        # enter new email address
        email_element = self.selenium.find_element(by=By.NAME, value="useremail_set-0-email")
        email_element.clear()
        email_element.send_keys(new_email)
        self.selenium.find_element(by=By.XPATH, value='//button[@name="_continue"]').click()
        self.wait_page_loaded()

        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')

        user_email = UserEmail.objects.get(email=new_email)
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
        self.wait_page_loaded()
        self.selenium.find_element(by=By.NAME, value="email").send_keys(new_email)
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')

        # try to confirm email
        confirmation_url = self.get_url_path_from_mail()
        self.selenium.get('%s%s' % (self.live_server_url, confirmation_url))
        self.wait_page_loaded()
        # we should find an error
        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-error"]')

    def test_self_add_useremail(self):
        self.login(username='GunnarScherf', password='gsf')
        new_email = "test@g10f.de"

        # add new email
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:emails')))
        self.wait_page_loaded()

        self.selenium.find_element(by=By.NAME, value="email").send_keys(new_email)
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')

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
        response = self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')
        self.assertIn(new_email, response.text)

        # check that login with new_mail and old email is possible
        self.logout()
        self.login_test(username='test@g10f.de', password='gsf')
        self.logout()
        self.login_test(username='gunnar@g10f.de', password='gsf')

        # set email as primary
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:emails')))
        self.wait_page_loaded()
        self.selenium.find_element(by=By.XPATH, value='//button[@name="set_primary"]').click()
        response = self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')
        self.assertIn(new_email, response.text)

        # delete email
        self.selenium.find_element(by=By.XPATH, value='//button[@name="delete"]').click()
        response = self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')
        self.assertIn("gunnar@g10f.de", response.text)

    def test_delete_user(self):
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:delete_profile')))
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()
        self.selenium.find_element(by=By.XPATH, value='//a[@href="%s"]' % reverse('auth:login'))

        # check if login is denied
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.find_element(by=By.XPATH, value='//form/div[@class="alert alert-danger"]')  # there should be a form error
        # there should be no logout link, because user is not logged in
        self.assertEqual(
            len(self.selenium.find_elements(by=By.XPATH, value='//ul/li/a[@href="%s"]' % reverse('auth:logout'))), 0)

    def test_change_password(self):
        username = 'GlobalAdmin'
        old_password = 'secret007'
        new_password = 'shRvubgx'

        self.login_test(username, old_password)

        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:password_change')))
        self.selenium.find_element(by=By.NAME, value="old_password").send_keys(old_password)
        self.selenium.find_element(by=By.NAME, value="new_password1").send_keys(new_password)
        self.selenium.find_element(by=By.NAME, value="new_password2").send_keys(new_password)
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.logout()

        self.login_test(username, new_password)

    def test_change_center(self):
        # change center as user
        self.login(username='GunnarScherf', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:organisationchange_me')))

        Select(self.selenium.find_element(by=By.NAME, value="organisation")).select_by_index(2)
        self.selenium.find_element(by=By.NAME, value="message").send_keys('Test')

        picture = os.path.abspath(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'))
        self.add_picture(picture)

        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()
        self.logout()

        # Accept center change as admin
        self.login('GlobalAdmin', 'secret007')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:organisationchange_list')))

        list_url = reverse('accounts:organisationchange_list')
        elems = self.selenium.find_elements(by=By.XPATH, value="//a[starts-with(@href, '%s')]" % list_url)
        # should be one element in the list
        elems[0].click()
        self.wait_page_loaded()
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()

        # check success message
        self.wait_page_loaded()
        self.selenium.find_element(by=By.CLASS_NAME, value="alert-success")
        self.logout()

    @override_settings(SSO_POST_RESET_LOGIN=False)
    def test_password_reset(self):
        self.logout()

        username = 'gunnar@g10f.de'
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:password_reset')))
        self.selenium.find_element(by=By.NAME, value="email").send_keys('gunnar@g10f.de')
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-error")), 0)

        path = self.get_url_path_from_mail()

        new_password = 'gsf1zghxyz'
        self.set_reset_password(path, new_password)
        self.login_test(username, new_password)

    @override_settings(SSO_POST_RESET_LOGIN=True)
    def test_password_post_reset_login(self):
        self.logout()

        username = 'gunnar@g10f.de'
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:password_reset')))
        self.wait_page_loaded()

        self.selenium.find_element(by=By.NAME, value="email").send_keys('gunnar@g10f.de')
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-error")), 0)

        path = self.get_url_path_from_mail()

        new_password = 'gsf1zghxyz'
        self.set_reset_password(path, new_password)
        self.login_test(username, new_password)

    def test_change_profile_success(self):
        new_first_name = 'Test'
        new_last_name = 'User'

        self.login(username='GunnarScherf', password='gsf')

        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:profile')))

        first_name = self.selenium.find_element(by=By.NAME, value="first_name")
        first_name.clear()
        first_name.send_keys(new_first_name)

        last_name = self.selenium.find_element(by=By.NAME, value="last_name")
        last_name.clear()
        last_name.send_keys(new_last_name)

        self.wait_page_loaded()
        continue_button = self.selenium.find_element(by=By.XPATH, value='//button[@type="submit"][@name="_continue"]')
        self.click(continue_button)
        self.wait_page_loaded()
        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-danger")), 0)

        first_name = self.selenium.find_element(by=By.NAME, value="first_name")
        self.assertEqual(first_name.get_attribute("value"), new_first_name)

        last_name = self.selenium.find_element(by=By.NAME, value="last_name")
        self.assertEqual(last_name.get_attribute("value"), new_last_name)

    def test_change_profile_failure(self):
        new_homepage = 'http:/home'  # wrong url format

        self.login(username='GunnarScherf', password='gsf')

        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:profile')))

        homepage = self.selenium.find_element(by=By.NAME, value="homepage")
        homepage.clear()
        homepage.send_keys(new_homepage)

        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()

        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-danger")), 1)

    def modify_app_role_to_user(self, user_id, add=True, number=1):
        id_application_role = f'//select[@id="id_application_roles_from"]/option[{number}]' if add else f'//select[@id="id_application_roles_to"]/option[{number}]'
        id_application_roles_modify_link = 'id_application_roles_add_link' if add else 'id_application_roles_remove_link'
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:update_user', kwargs={'uuid': user_id})))
        self.selenium.find_element(by=By.XPATH, value='//a[@href="#tab_application_roles"]').click()
        self.selenium.find_element(by=By.XPATH, value=id_application_role).click()
        self.selenium.find_element(by=By.ID, value=id_application_roles_modify_link).click()
        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()
        self.wait_page_loaded()
        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-success")), 1)

    def test_update_user_as_admin(self):
        applicationrole = ApplicationRole.objects.get(application__uuid="bc0ee635a536491eb8e7fbe5749e8111", role__name="Admin")
        user = get_user_model().objects.get(username='GunnarScherf')
        self.assertIn(applicationrole, user.application_roles.all())

        self.login(username='GlobalAdmin', password='secret007')
        # remove app role TestApp - Admin
        self.modify_app_role_to_user(user.uuid, add=False)
        self.assertNotIn(applicationrole, user.application_roles.all())

        # add app role TestApp - Admin
        self.modify_app_role_to_user(user.uuid, add=True)
        self.assertIn(applicationrole, user.application_roles.all())

    @override_settings(SSO_POST_RESET_LOGIN=False)
    def test_add_user_as_admin(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Global")
        allowed_orgs = Organisation.objects.filter(
            uuid__in=['31664dd38ca4454e916e55fe8b1f0745', '31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs)

    @override_settings(SSO_POST_RESET_LOGIN=True)
    def test_add_user_as_admin_post_reset_login(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Global")
        allowed_orgs = Organisation.objects.filter(
            uuid__in=['31664dd38ca4454e916e55fe8b1f0745', '31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs)

    def test_add_user_as_region(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Region")
        region = AdminRegion.objects.get_by_natural_key('0ebf2537fc664b7db285ea773c981404')
        allowed_orgs = Organisation.objects.filter(
            uuid__in=['31664dd38ca4454e916e55fe8b1f0745', '31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs, region=region)

    def test_add_user_as_center(self):
        applicationrole = ApplicationRole.objects.get(application__uuid=settings.SSO_APP_UUID, role__name="Center")
        allowed_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0745'])
        denied_orgs = Organisation.objects.filter(uuid__in=['31664dd38ca4454e916e55fe8b1f0746'])
        self.add_user(applicationrole=applicationrole, allowed_orgs=allowed_orgs, denied_orgs=denied_orgs)

    def test_remove_user_from_organisations(self):
        # remove user from all organisations where CenterAdmin has admin rights
        self.login(username='CenterAdmin', password='gsf')
        self.selenium.get('%s%s' % (
            self.live_server_url, reverse('accounts:update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})))
        self.wait_page_loaded()
        self.selenium.find_element(by=By.XPATH, value='//button[@name="_remove_org"]').click()
        self.wait_page_loaded()
        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')

        user = get_user_model().objects.get(username='GunnarScherf')
        user_organisations = user.organisations.all()
        for organisation in get_user_model().objects.get(username='CenterAdmin').organisations.all():
            self.assertNotIn(organisation, user_organisations)

    def test_remove_user_with_2_orgs_from_organisations(self):
        user = get_user_model().objects.get(username='GunnarScherf')
        # add user to TestCenter2
        user.add_organisation(Organisation.objects.get(uuid='31664dd38ca4454e916e55fe8b1f0746'))

        # remove user from all organisations where CenterAdmin has admin rights
        self.login(username='CenterAdmin', password='gsf')
        self.selenium.get('%s%s' % (self.live_server_url, reverse('accounts:update_user', kwargs={'uuid': 'a8992f0348634f76b0dac2de4e4c83ee'})))
        self.wait_page_loaded()
        remove_org_button = self.selenium.find_element(by=By.XPATH, value='//button[@name="_remove_org"]')
        self.click(remove_org_button)
        self.wait_page_loaded()
        self.selenium.find_element(by=By.XPATH, value='//div[@class="alert alert-success"]')

        user_organisations = user.organisations.all()
        for organisation in get_user_model().objects.get(username='CenterAdmin').organisations.all():
            self.assertNotIn(organisation, user_organisations)

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

        first_name = self.selenium.find_element(by=By.NAME, value="first_name")
        first_name.send_keys(new_first_name)

        last_name = self.selenium.find_element(by=By.NAME, value="last_name")
        last_name.send_keys(new_last_name)

        email = self.selenium.find_element(by=By.NAME, value="email")
        email.send_keys(new_email)

        gender = self.selenium.find_element(by=By.NAME, value="gender")
        gender.send_keys(new_gender)

        required_extra_fields = self.selenium.find_elements(by=By.XPATH, value='//span[@class="user-extra-form-fields"]//node()[@class="form-select" and @required]')
        for required_extra_field in required_extra_fields:
            if required_extra_field.tag_name == 'select':
                # select the first option with a non-empty value
                option = required_extra_field.find_elements(by=By.XPATH, value="option[@value and string-length(@value)!=0]")[0]
                option.click()
            # TODO: cases for other types of extra fields

        organisation = Select(self.selenium.find_element(by=By.NAME, value="organisations"))

        # test error case
        for org in denied_orgs:
            try:
                organisation.select_by_value(str(org.pk))
                raise Exception("Organisation with pk=%s should not be a possible option" % org)
            except NoSuchElementException:
                pass

        for org in allowed_orgs:
            organisation.select_by_value(str(org.pk))

        self.selenium.find_element(by=By.XPATH, value='//a[@href="#tab_application_roles"]').click()
        self.selenium.find_element(by=By.XPATH, value='//select[@id="id_application_roles_from"]/option[1]').click()
        self.selenium.find_element(by=By.ID, value="id_application_roles_add_link").click()

        self.selenium.find_element(by=By.TAG_NAME, value="form").submit()

        self.wait_page_loaded()
        self.assertEqual(len(self.selenium.find_elements(by=By.CLASS_NAME, value="alert-success")), 1)

        self.logout()
        # get the password reset link from the email to the new user
        # and set a new password
        path = self.get_url_path_from_mail()

        new_password = 'gsf1zghxyz'
        self.set_create_password(path, new_password)

        # check if the login link has the new app url as next parameter (redirect_to_after_first_login=True)
        if settings.SSO_POST_RESET_LOGIN:
            url = 'https://test.example.com'
        else:
            url = '%s?%s' % (reverse('auth:login'), urlencode({'next': 'https://test.example.com'}, safe='/'))

        self.selenium.find_element(by=By.XPATH, value='//a[@href="%s"]' % url)

        # login as new user with the new password
        self.login_test(new_email, new_password)

        # check if we have the Test App in the app roles
        self.selenium.find_element(by=By.XPATH, value='//a[@href="https://test.example.com"]')
