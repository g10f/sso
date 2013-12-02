"""
Allow to use an email address instead of the user id as the
primary id
Taken from a posting on the Django mailing list.
Thanks to Vasily Sulatskov for sending this to the list.
"""
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import re

EMAIL_RE = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'  # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

            
class EmailBackend(ModelBackend):
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
