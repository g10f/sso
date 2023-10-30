import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from sso.accounts.models import User, Application, ApplicationRole
from sso.api.views.generic import JsonDetailView
from sso.api.views.home import UUIDS, replace_with_param_name
from sso.utils.url import get_base_url

logger = logging.getLogger(__name__)


class ApplicationView(JsonDetailView):
    model = Application
    http_method_names = ['get', 'options']

    def get_object_data(self, request, obj):
        app_roles = self.request.user.get_administrable_application_roles(Q(application__uuid=self.kwargs['uuid']))
        data = {
            'id': '%s' % obj.uuid.hex,
            'order': obj.order,
            'link': {
                'href':  obj.url,
                'title': obj.title,
                'global_navigation': obj.global_navigation,
            },
            'roles': [app_role.role.name for app_role in app_roles]
        }
        return data


def read_permission(request, obj):
    """
    user is the authenticated user
    permission to read the obj data
    """
    user = request.user
    required_scope = 'role'
    if not user.is_authenticated:
        return False, 'User not authenticated'
    if required_scope and required_scope not in request.scopes:
        return False, "%s not in scope '%s'" % (required_scope, request.scopes)
    if not user.has_perm('accounts.read_user'):
        return False, "User has no permission '%s" % 'accounts.read_user'
    elif not user.has_user_access(obj.uuid):
        return False, "User has no access to object"
    else:
        return True, None


def replace_permission(request, obj):
    """
    user is the authenticated user
    permission to change user the obj
    """
    user = request.user
    required_scope = 'role'
    if not user.is_authenticated:
        return False, 'User not authenticated'
    if required_scope and required_scope not in request.scopes:
        return False, "%s not in scope '%s'" % (required_scope, request.scopes)
    if not user.has_perm('accounts.change_user'):
        return False, "User has no permission '%s" % 'accounts.change_user'
    elif not user.has_user_access(obj.uuid):
        return False, "User has no access to object"
    else:
        return True, None

class UserApplicationRolesView(JsonDetailView):
    model = User
    http_method_names = ['get', 'options']

    permissions_tests = {
        'read': read_permission,
        'create': replace_permission,
        'delete': replace_permission,
    }

    def get_operations(self):
        base_uri = get_base_url(self.request)
        template = "%s%s" % (base_uri, replace_with_param_name(reverse(
            'api:v2_user_app_role', kwargs={'uuid': self.object.uuid.hex, 'app_uuid': self.kwargs['app_uuid'], 'role': UUIDS['role']})))
        return {
            'create': {
                '@type': 'CreateResourceOperation',
                'method': 'PUT',
                'template': template
            },
            'delete': {
                '@type': 'DeleteResourceOperation',
                'method': 'DELETE',
                'template': template
            }
        }

    def get_object(self, queryset=None):
        user = super().get_object(queryset)
        # check required_scope before returning any information
        app = Application.objects.get_by_natural_key(self.kwargs['app_uuid'])
        if app.required_scope and not app.required_scope in self.request.scopes:
            raise Http404(f"Access to '{app}' roles requires scope '{app.required_scope}'.")
        self.app_roles = user.get_applicationroles().filter(application__uuid=self.kwargs['app_uuid'])
        return user

    def get_object_data(self, request, obj):
        base_uri = get_base_url(self.request)
        data = {
            'member': [
                {
                    '@id': "%s%s" % (base_uri, replace_with_param_name(reverse(
                        'api:v2_user_app_role', kwargs={'uuid': self.object.uuid.hex, 'app_uuid': self.kwargs['app_uuid'], 'role': app_role.role.name}))),
                    'name': app_role.role.name

                } for app_role in self.app_roles
            ],
            'total_items': self.app_roles.count()
        }
        return data


class UserApplicationRoleView(JsonDetailView):
    model = User
    http_method_names = ['get', 'put', 'delete', 'options']

    permissions_tests = {
        'read': read_permission,
        'create': replace_permission,
        'delete': replace_permission,
    }
    operations = {
        'create': {'@type': 'CreateResourceOperation', 'method': 'PUT'},
        'delete': {'@type': 'DeleteResourceOperation', 'method': 'DELETE'},
    }

    def get_operations(self):
        base_uri = get_base_url(self.request)
        template = "%s%s" % (base_uri, replace_with_param_name(reverse(
            'api:v2_user_app_role', kwargs={'uuid': self.object.uuid.hex, 'app_uuid': self.kwargs['app_uuid'], 'role': self.kwargs['role']})))
        return {
            'delete': {
                '@type': 'DeleteResourceOperation',
                'method': 'DELETE',
                'template': template
            }
        }

    def get_object(self, queryset=None):
        try:
            self.object = super().get_object(queryset)
        except Http404 as e:
            raise ObjectDoesNotExist(e)

        # check if app exists and throw exception if not exists
        Application.objects.get_by_natural_key(self.kwargs['app_uuid'])

        try:
            # check if user has app role
            self.app_role = self.object.get_applicationroles().get(application__uuid=self.kwargs['app_uuid'], role__name=self.kwargs['role'])
            # check if request.user is allowed to manage the role
            if self.app_role != self.request.user.get_administrable_application_roles(Q(application__uuid=self.kwargs['app_uuid'], role__name=self.kwargs['role'])).first():
                logger.warning(f"User request.user is not allowed to manage {self.app_role}")
                raise Http404(f"Application role not found")
        except ApplicationRole.DoesNotExist:
            raise Http404(f"Application role not found")
        return self.object

    def get_object_data(self, request, object):
        if self.app_role:
            return {'name': self.app_role.role.name}
        else:
            return {}

    def delete_object(self, request, obj):
        app_role = self.request.user.get_administrable_application_roles(Q(application__uuid=self.kwargs['app_uuid'], role__name=self.kwargs['role'])).first()
        # check if app_role exists
        if app_role is not None:
            obj.application_roles.remove(app_role)

    def put(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.check_permission('create', self.object)
            context = self.get_context_data()
            return self.render_to_response(context, status=200)
        except Http404:
            # check is on user level
            self.check_permission('create', self.object)
            self.app_role = self.request.user.get_administrable_application_roles(Q(application__uuid=self.kwargs['app_uuid'], role__name=self.kwargs['role'])).first()
            # check if app_role exists
            if self.app_role is None:
                raise ObjectDoesNotExist(f"Role {self.kwargs['role']} not found.")
                # return self.render_to_response({}, status=400)

            context = self.get_context_data()
            self.object.application_roles.add(self.app_role)
            return self.render_to_response(context, status=201)
