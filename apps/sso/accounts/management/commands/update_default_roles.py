# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from django.conf import settings

from sso.accounts import models

def get_app_roles(app_roles_dict):
    app_roles = []
    for _app_role in app_roles_dict:
        application = models.Application.objects.get(uuid=_app_role['uuid'])
        for roles_name in _app_role['roles']:
            role = models.Role.objects.get(name=roles_name)
            app_roles += [models.ApplicationRole.objects.get(application=application, role=role)]
    return app_roles
    
def remove_redundant_app_roles(role_profile):
    user_list = models.User.objects.filter(role_profiles=role_profile, is_active=True)
    
    for user in user_list:
        application_roles = list(role_profile.application_roles.all())
        user.application_roles.remove(*application_roles)

class Command(NoArgsCommand):
    help = '...'  # @ReservedAssignment
    
    def handle_noargs(self, **options):
        default_role_profile = models.User.get_default_role_profile()
        center_admin_profile = models.User.get_default_admin_profile()
        buddhafabrik_intern = models.RoleProfile.objects.get(uuid='1edb18db15cf47e7a4649d1de0484804')
        
        user_list = models.User.objects.filter(is_active=True)
        for user in user_list:
            user.role_profiles.add(default_role_profile)
        
        sso_center = models.ApplicationRole.objects.get(application__uuid=settings.SSO_CUSTOM['APP_UUID'], role__name='Center')
        user_list = models.User.objects.filter(application_roles=sso_center, is_active=True)
        for user in user_list:
            user.role_profiles.add(center_admin_profile)

        remove_redundant_app_roles(default_role_profile)
        remove_redundant_app_roles(center_admin_profile)
        remove_redundant_app_roles(buddhafabrik_intern)
