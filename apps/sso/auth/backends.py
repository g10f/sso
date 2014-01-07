from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
import re

EMAIL_RE = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'  # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


class SSOBackend(ModelBackend):
    def get_group_permissions(self, user_obj, obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        Additionally to the standard Django groups, the groups which are associated through the roles are considered. 
        """
        if user_obj.is_anonymous() or obj is not None:
            return set()
        if not hasattr(user_obj, '_sso_group_perm_cache'):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                # this is standard django model backend behavior
                groups_query = Q(group__user=user_obj)  
                
                # this comes through groups associated to roles
                groups_from_roles_query = Q(group__role__applicationrole__user=user_obj, group__role__applicationrole__application__uuid=settings.APP_UUID)
                groups_from_roles_query |= Q(group__role__applicationrole__roleprofile__user=user_obj, group__role__applicationrole__application__uuid=settings.APP_UUID)
                
                perms = Permission.objects.filter(groups_query | groups_from_roles_query)
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            user_obj._sso_group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._sso_group_perm_cache
    

class EmailBackend(SSOBackend):
    """Authenticate using email or username"""
    def authenticate(self, username=None, password=None):
        #If username is an email address, then try to pull it up
        user_model = get_user_model()
        if EMAIL_RE.search(username):
            user = user_model.objects.filter(email__iexact=username)
            if user.count() > 0:
                user = user[0]
                if user.check_password(password):
                    return user
        try:  # username
            user = user_model.objects.get(username=username)
            if user.check_password(password):
                return user
        except ObjectDoesNotExist:
            return None
