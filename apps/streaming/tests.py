# -*- coding: utf-8 -*-
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from .backends import StreamingBackend
from django.contrib.auth import get_user_model

class StreamingMethodTests(TestCase):

    fixtures = ['initial_data.json', 'app_roles.json', 'test_streaming_user.json', 'test_user_data.json', 'test_app_roles.json']
    
    def setUp(self):
        self.client = Client()

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
        
    def test_create_center_account(self):
        backend = StreamingBackend()
        user = backend.authenticate("testcenter1@example.com", "geheim08")
        self.assertIsNotNone(user)        
        
        self.assertEqual(user.first_name, 'BuddhistCenter')
        self.assertEqual(user.last_name, 'testcenter1')
        self.assertGreater(len(user.application_roles.all()), 1)
        app_roles = user.application_roles.all().values('application__uuid', 'role__name')
        # SSO
        self.assertIn({'application__uuid': settings.APP_UUID, 'role__name': 'Center'}, app_roles)  
        # Streaming
        self.assertIn({'application__uuid': 'c362bea58c67457fa32234e3178285c4', 'role__name': 'Center'}, app_roles)  
        # Dharmashop Home
        self.assertIn({'application__uuid': 'e4a281ef13e1484b93fe4b7cc66374c8', 'role__name': 'User'}, app_roles)  
        # Dharma Shop 108 - West Europe
        self.assertIn({'application__uuid': '35efc492b8f54f1f86df9918e8cc2b3d', 'role__name': 'User'}, app_roles)
        # Wiki 
        self.assertIn({'application__uuid': 'b8c38af479e54f4c94faf9d8184528fe', 'role__name': 'User'}, app_roles) 
