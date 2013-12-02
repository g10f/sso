# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test.client import Client
from .backends import StreamingBackend
from sso.accounts.models import ApplicationRole, Application, Role
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

class StreamingMethodTests(TestCase):

    fixtures = ['initial_data.json', 'test_streaming_user.json', 'test_user_data.json']
    
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
        
        self.assertEqual(user.is_staff, True)
        self.assertEqual(user.first_name, 'BuddhistCenter')
        self.assertEqual(user.last_name, 'testcenter1')
        self.assertEqual(len(user.groups.all()), 1)
        self.assertEqual(user.groups.all()[0], Group.objects.get(name='OrganisationUserAdmin'))
        
        dharma_shop_west_europe = Application.objects.get(uuid='35efc492b8f54f1f86df9918e8cc2b3d')
        wiki = Application.objects.get(uuid='b8c38af479e54f4c94faf9d8184528fe')
        user_role = Role.objects.get(name='User')
        guest_role = Role.objects.get(name='Guest')
        dharma_shop_west_europe_user = ApplicationRole.objects.get(application=dharma_shop_west_europe, role=user_role)
        dharma_shop_west_europe_guest = ApplicationRole.objects.get(application=dharma_shop_west_europe, role=guest_role)
        wiki_user = ApplicationRole.objects.get(application=wiki, role=user_role)
        
        applicationroles = user.get_applicationroles()
        self.assertIn(dharma_shop_west_europe_user, applicationroles)
        self.assertIn(dharma_shop_west_europe_guest, applicationroles)
        self.assertIn(wiki_user, applicationroles)
