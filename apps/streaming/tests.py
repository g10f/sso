# -*- coding: utf-8 -*-
try:
    from urllib.parse import urlsplit
except ImportError:     # Python 2
    from urlparse import urlsplit
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from .backends import StreamingBackend
from django.contrib.auth import get_user_model, authenticate
from django.core.urlresolvers import reverse
from django.core import mail

from sso.organisations.models import Organisation
from sso.accounts.forms import PasswordResetForm

class StreamingMethodTests(TestCase):

    fixtures = ['initial_data.json', 'app_roles.json', 'test_streaming_user.json', 'test_l10n_data.xml', 'test_organisation_data.json', 'test_app_roles.json', 'test_user_data.json']
    
    def setUp(self):
        self.client = Client()

    def test_successful_login(self):
        
        backend = StreamingBackend()
        user = backend.authenticate("user07@example.com", "geheim07")
        self.assertIsNotNone(user)
        
    def test_user_not_found(self):
        
        backend = StreamingBackend()
        user = backend.authenticate("user07xy@example.com", "geheim07")
        self.assertIsNone(user)

    def test_change_email_and_password_reset(self):
        """
        try password reset with email should succeed
        """
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'user07@example.com'})
        self.assertEqual(response.status_code, 302)
        (scheme, netloc, path, query, fragment) = urlsplit(response.url)  # @UnusedVariable
        self.assertEqual(path, reverse('accounts:password_resend_done'))

        outbox = getattr(mail, 'outbox')
        self.assertNotEqual(outbox[-1].body.find('geheim07'), -1) 

        """
        successful authentication
        """
        backend = StreamingBackend()
        user = backend.authenticate("user07@example.com", "geheim07")
        self.assertIsNotNone(user)
        # change email
        user.email = "new@example.com"
        user.save()
        
        """
        password reset with old email should fail
        """
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'user07@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PasswordResetForm.error_messages['unknown'], response.context['form'].errors['email'][0])

    def test_streaming_authentication_is_used_only_for_one_successful_login(self):
        
        backend = StreamingBackend()
        user = backend.authenticate("user07@example.com", "geheim07")
        self.assertIsNotNone(user)
        
        user.email = "new@example.com"
        user.set_password("123456")
        user.save()
        
        user = backend.authenticate("user07@example.com", "geheim07")
        self.assertIsNone(user)
        
        # Do some database work
        user = get_user_model().objects.get(email="new@example.com")
        user.set_password("1234567")
        user.save()
    
    def test_create_2nd_user_with_same_name(self):
        backend = StreamingBackend()
        user = backend.authenticate("user07@example.com", "geheim07")
        self.assertIsNotNone(user)
        user.username = "admin@example.com"
        user.save()
        
        user = backend.authenticate("admin@example.com", "geheim08")
        self.assertIsNotNone(user)
        
    def test_login_with_streaming_user_where_email_exists(self):
        """
        user gunnar@g10f.de exist already in the sso and in the streaming database with a different password
        """
        # authenticate at SSO
        user = authenticate(username="gunnar@g10f.de", password="gsf")
        self.assertIsNotNone(user)

        # authenticate at Streaming 
        user = authenticate(username="gunnar@g10f.de", password="geheim08")
        self.assertIsNotNone(user)

        # after 1 successful authentication at streaming, SSO is always used
        # authenticate at SSO (new password from streaming)
        user = authenticate(username="gunnar@g10f.de", password="gsf")
        self.assertIsNone(user)

        # authenticate at SSO
        user = authenticate(username="gunnar@g10f.de", password="geheim08")
        self.assertIsNotNone(user)
        user.set_password("123456")
        user.save()

        # authenticate at SSO and Streaming is failing (old streaming password is not possble anymore)
        user = authenticate(username="gunnar@g10f.de", password="geheim08")
        self.assertIsNone(user)
        
    def test_create_center_account(self):
        backend = StreamingBackend()
        user = backend.authenticate("testcenter1@example.com", "geheim08")
        self.assertIsNotNone(user)        
        
        self.assertEqual(user.first_name, 'BuddhistCenter')
        self.assertEqual(user.last_name, 'testcenter1')
        app_roles = user.get_applicationroles().values('application__uuid', 'role__name')
        role_profiles = user.role_profiles.all().values('uuid')

        self.assertIn({'application__uuid': '35efc492b8f54f1f86df9918e8cc2b3d', 'role__name': 'User'}, app_roles)  # Dharma Shop 108 - West Europe
        self.assertIn({'uuid': settings.SSO_CUSTOM['DEFAULT_ADMIN_PROFILE_UUID']}, role_profiles)  # SSO        
        self.assertIn({'uuid': settings.SSO_CUSTOM['DEFAULT_ROLE_PROFILE_UUID']}, role_profiles)  

        self.assertQuerysetEqual(user.organisations.all(), [repr(x) for x in Organisation.objects.filter(uuid='31664dd38ca4454e916e55fe8b1f0745')])
        
    def test_create_center_account_without_a_center_email(self):
        backend = StreamingBackend()
        user = backend.authenticate("admin@example.com", "geheim08")
        
        self.assertEqual(user.first_name, 'BuddhistCenter')
        self.assertEqual(user.last_name, 'admin')
        role_profiles = user.role_profiles.all().values('uuid')

        self.assertIn({'uuid': settings.SSO_CUSTOM['DEFAULT_ADMIN_PROFILE_UUID']}, role_profiles)  
        self.assertIn({'uuid': settings.SSO_CUSTOM['DEFAULT_ROLE_PROFILE_UUID']}, role_profiles)  
