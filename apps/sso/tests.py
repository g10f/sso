import os

import time
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse


class SSOSeleniumTests(StaticLiveServerTestCase):
    # fixtures = ['user_data.json']

    @classmethod
    def setUpClass(cls):
        os.environ['THROTTLING_DISABLED'] = 'True'
        # capabilities = DesiredCapabilities.FIREFOX.copy()
        # capabilities['marionette'] = True
        # capabilities['binary'] = '/opt/mozilla/geckodriver'
        # cls.selenium = WebDriver(firefox_binary=FirefoxBinary(log_file=open('./ff.log', 'w')))
        # cls.selenium = WebDriver(capabilities=capabilities)
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(1)

    @classmethod
    def tearDownClass(cls):
        del os.environ['THROTTLING_DISABLED']
        cls.selenium.quit()
        super().tearDownClass()

    def wait_until(self, callback, timeout=10):
        """
        Helper function that blocks the execution of the tests until the
        specified callback returns a value that is not falsy. This function can
        be called, for example, after clicking a link or submitting a form.
        See the other public methods that call this function for more details.
        """
        from selenium.webdriver.support.wait import WebDriverWait
        WebDriverWait(self.selenium, timeout).until(callback)

    def wait_loaded_tag(self, tag_name, timeout=10):
        """
        Helper function that blocks until the element with the given tag name
        is found on the page.
        """
        self.wait_until(
            lambda driver: driver.find_element(by=By.TAG_NAME, value=tag_name),
            timeout
        )

    def wait_page_loaded(self):
        """
        Block until page has started to load.
        """
        from selenium.common.exceptions import TimeoutException
        try:
            # Wait for the next page to be loaded
            self.wait_loaded_tag('body')
        except TimeoutException:
            # IE7 occasionnally returns an error "Internet Explorer cannot
            # display the webpage" and doesn't load the next page. We just
            # ignore it.
            pass

    def login(self, username, password):
        driver = self.selenium
        driver.get('%s%s' % (self.live_server_url, reverse('auth:login')))
        self.wait_page_loaded()
        driver.find_element(by=By.NAME, value="username").send_keys(username)
        driver.find_element(by=By.NAME, value="password").send_keys(password)
        driver.find_element(by=By.TAG_NAME, value="form").submit()

        # Wait until the response is received
        self.wait_page_loaded()

    def logout(self):
        self.selenium.get('%s%s' % (self.live_server_url, reverse('auth:logout')))
        # Wait until the response is received
        self.wait_page_loaded()

    def click(self, element):
        self.selenium.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(.5)
        element.click()

    def add_picture(self, picture):
        self.selenium.find_element(by=By.XPATH, value='//input[@type="file"]').send_keys(picture)
        self.selenium.find_element(by=By.ID, value="crop").click()
