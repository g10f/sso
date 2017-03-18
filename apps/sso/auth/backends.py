import logging
from django.core.exceptions import ObjectDoesNotExist
from sso.accounts.models import User
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
import re

logger = logging.getLogger(__name__)


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
        if user_obj.is_anonymous or obj is not None:
            return set()
        if not hasattr(user_obj, '_sso_group_perm_cache'):
            if user_obj.is_superuser:
                perms = Permission.objects.all()
            else:
                perms = user_obj.get_group_and_role_permissions()
            perms = perms.values_list('content_type__app_label', 'codename').order_by()
            user_obj._sso_group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._sso_group_perm_cache

    def get_user(self, user_id):
        try:
            return User.objects.get(uuid=user_id)
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(e)
        return None


class EmailBackend(SSOBackend):
    """Authenticate using email or username"""
    def authenticate(self, username=None, password=None):
        # If username is an email address, then try to pull it up
        if EMAIL_RE.search(username):
            try:
                user = User.objects.get_by_confirmed_or_primary_email(username)
                if user.check_password(password):
                    return user
            except ObjectDoesNotExist:
                pass
        try:  # username
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except ObjectDoesNotExist:
            return None
