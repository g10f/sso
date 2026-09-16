import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse
from sso.oauth2.tests import OAuth2BaseTestCase


class UserInfoTests(OAuth2BaseTestCase):

    def get_userinfo(self, scope="openid profile email", **extra):
        authorization = self.get_authorization(scope=scope)
        return self.client.get(reverse('oauth2:userinfo'), HTTP_AUTHORIZATION=authorization, **extra)

    def test_discovery_points_to_userinfo(self):
        configuration = self.client.get(reverse('openid-configuration')).json()
        self.assertTrue(configuration['userinfo_endpoint'].endswith(reverse('oauth2:userinfo')))

    def test_standard_claims(self):
        user = get_user_model().objects.get(username='GunnarScherf')
        response = self.get_userinfo()
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
        data = response.json()
        self.assertEqual(data['sub'], user.uuid.hex)
        self.assertEqual(data['name'], user.get_full_name())
        self.assertEqual(data['preferred_username'], user.username)
        self.assertEqual(data['email'], user.primary_email().email)
        self.assertIsInstance(data['email_verified'], bool)
        self.assertIsInstance(data['updated_at'], int)
        # the user has no picture and empty claims are omitted
        self.assertNotIn('picture', data)
        # no fields of the v2 users api
        self.assertNotIn('@id', data)
        self.assertNotIn('organisations', data)

    def test_picture_is_url_string(self):
        user = get_user_model().objects.get(username='GunnarScherf')
        with open(os.path.join(settings.BASE_DIR, 'sso/static/img/face-cool.png'), 'rb') as f:
            user.picture.save('face-cool.png', ContentFile(f.read()))

        data = self.get_userinfo().json()
        self.assertIsInstance(data['picture'], str)
        self.assertTrue(data['picture'].startswith('http://testserver/'))

    def test_claims_depend_on_scopes(self):
        data = self.get_userinfo(scope="openid email").json()
        self.assertIn('email', data)
        self.assertNotIn('name', data)
        self.assertNotIn('updated_at', data)

    def test_post_with_access_token_in_body(self):
        access_token = self.get_authorization().split()[1]
        response = self.client.post(reverse('oauth2:userinfo'), {'access_token': access_token})
        self.assertEqual(response.status_code, 200)
        self.assertIn('sub', response.json())

    def test_cors_header(self):
        response = self.get_userinfo(HTTP_ORIGIN='https://example.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

    def test_without_access_token(self):
        response = self.client.get(reverse('oauth2:userinfo'))
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response['WWW-Authenticate'].startswith('Bearer'))

    def test_cookie_authentication_is_not_allowed(self):
        self.client.login(username='GunnarScherf', password='gsf')
        response = self.client.get(reverse('oauth2:userinfo'))
        self.assertEqual(response.status_code, 401)

    def test_invalid_access_token(self):
        response = self.client.get(reverse('oauth2:userinfo'), HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(response.status_code, 401)
        self.assertIn('error="invalid_token"', response['WWW-Authenticate'])
        self.assertEqual(response.json()['error'], 'invalid_token')

    def test_access_token_is_invalid_after_password_change(self):
        authorization = self.get_authorization()
        user = get_user_model().objects.get(username='GunnarScherf')
        user.set_password('a new password 123')
        user.save()
        response = self.client.get(reverse('oauth2:userinfo'), HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 401)

    def test_without_openid_scope(self):
        response = self.get_userinfo(scope="profile email")
        self.assertEqual(response.status_code, 401)
        self.assertIn('error="invalid_token"', response['WWW-Authenticate'])
