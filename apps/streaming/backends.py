import logging
import re

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from django.db import IntegrityError
from sso.accounts.models import UserAssociatedSystem, Application
from sso.organisations.models import Organisation
from models import StreamingUser

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'  # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


def create_user(username, email):
    for i in range(0, 99):
        try:
            with transaction.atomic():
                if i > 0:
                    new_username = '%s%d' % (username, i)
                else:
                    new_username = username
                user = get_user_model()(username=new_username, email=email)
                user.save()
                return user
        except IntegrityError:
            if i == 99:
                print "IntegrityError in saving user %s" % email
                raise


def create_or_get_streaming_user(username, email, password, is_center, is_subscriber, is_admin):
    try:
        user = get_user_model().objects.get(email__iexact=email)
        user.set_password(password)
        user.save()
        return user
    except ObjectDoesNotExist:
        user = create_user(username, email)
        
    user.set_password(password)
    user.is_subscriber = is_subscriber
    user.save()
    
    if is_center:
        try:
            organisation = Organisation.objects.get(email__iexact=email)
            user.is_center = is_center
            user.organisations.add(organisation)
            user.first_name = 'BuddhistCenter'
            user.last_name = email.split('@')[0]
            user.save()            
        except ObjectDoesNotExist:
            pass

    user.add_default_roles()

    return user

    
class StreamingBackend(object):
    supports_inactive_user = True
    
    def authenticate(self, username=None, password=None):
        try:
            # Streaming user id's are email addresses
            if not EMAIL_RE.search(username):
                return None
            
            userassociatedsystem = UserAssociatedSystem.objects.filter(userid__iexact=username, application__uuid=settings.SSO_CUSTOM['STREAMING_UUID']).first()

            # if the user was already authenticated once successful against the streaming database,
            # we use the sso database for password checking      
            if userassociatedsystem:
                return None
            sql = "SELECT id_nr, password FROM streaming_user WHERE LOWER(email) LIKE LOWER(%(email)s)"
            streaming_user = StreamingUser.objects.raw(sql, {'email': username})[0]
                        
            if streaming_user.check_password(password):
                email = username
                # truncate the length if needed
                username = username[:28]
                
                is_center = True if (streaming_user.center == 'J') else False
                is_subscriber = True if (streaming_user.subscriber == 'J') else False
                is_admin = True if (streaming_user.admin == 'J') else False
                
                user = create_or_get_streaming_user(username, email, password, is_center, is_subscriber, is_admin)
                # create UserAssociatedSystem
                if not userassociatedsystem:
                    application = Application.objects.get_or_create(uuid=settings.SSO_CUSTOM['STREAMING_UUID'], defaults={'title': 'Streaming', })[0]
                    UserAssociatedSystem.objects.get_or_create(userid=email, user=user, application=application)
                return user
            
            return None
        except IndexError:
            return None
        except Exception, e:
            logger.exception(e)
            return None
    
    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None
