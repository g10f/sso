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

class EmailsSeleniumTests(SSOSeleniumTests):
    pass