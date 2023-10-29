from uritemplate import expand

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from sso.accounts.models import User
from sso.oauth2.tests import OAuth2BaseTestCase

data = {
    'user_id': 'a8992f0348634f76b0dac2de4e4c83ee',
    'app_id': 'bc0ee635a536491eb8e7fbe5749e8111',
    'special_app_id': '8478dbea8d594b2780fa76a6ef822ad2',
    'role': 'Staff'
}


class AppRolesApiTests(OAuth2BaseTestCase):
    def get_url_from_api_home(self, name, **kwargs):
        if kwargs is None:
            kwargs = {}
        response = self.client.get(reverse('api:home'))
        home = response.json()
        return expand(home[name], kwargs)

    def test_app_role(self):
        user_app_roles_url = self.get_url_from_api_home('user_app_roles', user_id=data['user_id'], app_id=data['app_id'])

        # get token with 'role' scope
        authorization = self.get_authorization_with_client_credentials(client_id='b740653ccaa14feba7e223c609896672', scope="openid role")

        # get list of roles for user and app
        user_app_roles = self.client.get(user_app_roles_url, HTTP_AUTHORIZATION=authorization).json()
        self.assertIn('operation', user_app_roles, user_app_roles_url)
        self.assertEqual(len(user_app_roles['operation']), 2, user_app_roles_url)

        # user_app_roles
        delete_user_app_role_op = next(filter(lambda x: x['@type'] == 'DeleteResourceOperation', user_app_roles['operation']))
        create_user_app_role_op = next(filter(lambda x: x['@type'] == 'CreateResourceOperation', user_app_roles['operation']))

        # delete Admin role
        user_app_role_url = user_app_roles['member'][0]['@id']
        response = self.client.delete(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 204, user_app_role_url)

        # delete Admin role again
        user_app_role_url = user_app_roles['member'][0]['@id']
        response = self.client.delete(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 204, user_app_role_url)

        # Add Admin role response code 201 created
        response = self.client.put(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        user_app_role = response.json()
        self.assertEqual(response.status_code, 201, user_app_role_url)
        self.assertEqual(user_app_role['@id'], user_app_role_url, user_app_role_url)

        # Add Admin role again (response code 200 instead of 201 created)
        response = self.client.put(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        user_app_role = response.json()
        self.assertEqual(response.status_code, 200, user_app_role_url)
        self.assertEqual(user_app_role['@id'], user_app_role_url, user_app_role_url)

        # Add non-existing Dummy role
        user_app_role_url = expand(create_user_app_role_op['template'], {'role': 'Dummy'})
        response = self.client.put(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 404, user_app_role_url)
        self.assertIn('error', response.json(), user_app_roles_url)
        self.assertIn("Role Dummy not found", response.json()['error_description'], user_app_roles_url)

        # Delete non-existing Dummy role
        user_app_role_url = expand(delete_user_app_role_op['template'], {'role': 'Dummy'})
        response = self.client.delete(user_app_role_url, HTTP_AUTHORIZATION=authorization)
        self.assertEqual(response.status_code, 204, user_app_role_url)

        # test error use cases
        service_user = User.objects.get_by_natural_key("TestClientService")
        content_type = ContentType.objects.get_for_model(User)
        access_all_users_permission = Permission.objects.get(codename="access_all_users", content_type=content_type)
        read_user_permission = Permission.objects.get(codename="read_user", content_type=content_type)

        # User needs access to user object
        service_user.user_permissions.remove(access_all_users_permission)

        user_app_roles = self.client.get(user_app_roles_url, HTTP_AUTHORIZATION=authorization).json()
        self.assertIn('error', user_app_roles, user_app_roles_url)
        self.assertEqual('not_authorized', user_app_roles['error'], user_app_roles_url)
        self.assertIn("User has no access to object", user_app_roles['error_description'], user_app_roles_url)

        # User needs accounts.read_user permission
        service_user.user_permissions.add(access_all_users_permission)
        service_user.user_permissions.remove(read_user_permission)

        user_app_roles = self.client.get(user_app_roles_url, HTTP_AUTHORIZATION=authorization).json()
        self.assertIn('error', user_app_roles, user_app_roles_url)
        self.assertEqual('not_authorized', user_app_roles['error'], user_app_roles_url)
        self.assertIn("User has no permission 'accounts.read_user'", user_app_roles['error_description'], user_app_roles_url)

        # get token without 'role' scope
        authorization = self.get_authorization_with_client_credentials(client_id='b740653ccaa14feba7e223c609896672', scope="openid")
        user_app_roles_url = self.get_url_from_api_home('user_app_roles', user_id=data['user_id'], app_id=data['app_id'])
        response = self.client.get(user_app_roles_url, HTTP_AUTHORIZATION=authorization)
        self.assertIn('error', response.json(), user_app_roles_url)
        self.assertIn('role not in scope', response.json()['error_description'], user_app_roles_url)

    def test_app_with_required_scope_role(self):
        user_app_roles_url = self.get_url_from_api_home('user_app_roles', user_id=data['user_id'], app_id=data['special_app_id'])

        # get token with 'role' scope
        authorization = self.get_authorization_with_client_credentials(client_id='b740653ccaa14feba7e223c609896672', scope="openid role")

        # get list of roles for user and app
        response = self.client.get(user_app_roles_url, HTTP_AUTHORIZATION=authorization).json()
        self.assertIn('error', response, user_app_roles_url)
        self.assertIn("Access to 'Test App with required scope' roles requires scope 'special'", response['error_description'], user_app_roles_url)
