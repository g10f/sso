# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from streaming.models import StreamingUser
from django.conf import settings
from sso.accounts.models import Application, UserAssociatedSystem, Organisation, User
from django.utils.text import capfirst
from django.db import transaction
from django.db import IntegrityError
from django.contrib.auth.hashers import make_password

import logging
logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    help = "Load Streaming User."    # @ReservedAssignment
    
    def handle(self, *args, **options):
        if len(args) > 0:
            self.url = args[0]
        try:
            load_streaming_users()
        except Exception, e:
            logger.error(e)


def create_user(username, email, password, is_center, is_subscriber, first_name, last_name, date_joined, last_login):
    for i in range(0, 99):
        try:
            with transaction.atomic():
                if i > 0:
                    new_username = '%s%d' % (username, i)
                else:
                    new_username = username
                user = User(username=new_username, email=email, password=make_password(password), is_center=is_center, is_subscriber=is_subscriber,
                            first_name=first_name, last_name=last_name, date_joined=date_joined, last_login=last_login)
                user.save()
                return user
        except IntegrityError:
            if i == 99:
                print "IntegrityError in saving user %s" % email
                raise


def create_new_user_from_streaming(streaming_user):
    try:
        email = streaming_user.email
        password = streaming_user.password.decode('base64')
        is_center = True if (streaming_user.center == 'J') else False
        is_subscriber = True if (streaming_user.subscriber == 'J') else False
        date_joined = streaming_user.created
        last_login = streaming_user.created
        
        if is_center:
            first_name = 'BuddhistCenter'
            last_name = capfirst(email.split('@')[0])
            username = u"%s%s" % (first_name, last_name)
            username = username[:29]  # max 30 chars
        else:
            first_name = ''
            last_name = ''
            username = email[:29]
        
        user = create_user(username, email, password, is_center, is_subscriber, first_name, last_name, date_joined, last_login)
            
        if is_center:
            organisation = Organisation.objects.filter(email__iexact=email).first()
            if organisation:
                user.organisations.add(organisation)
    
        user.add_default_roles()
    
        return user
    except Exception, e:
        print "error create_new_user_from_streaming %s. %s" % (streaming_user.email, e)
    return None


def load_streaming_users():
    
    streaming_users = StreamingUser.objects.all()
    application = Application.objects.get_or_create(uuid=settings.SSO_CUSTOM['STREAMING_UUID'], defaults={'title': 'Streaming'})[0]
    
    for streaming_user in streaming_users:
        email = streaming_user.email
        
        if UserAssociatedSystem.objects.filter(userid=email, application=application).exists():
            #print 'user exists in UserAssociatedSystem: %s ' % (email)  # , UserAssociatedSystem.objects.filter(userid=email, application=application)[0].user.email)
            continue
        elif User.objects.filter(email=email).exists():
            #print 'user exists in User:                 %s ' % email
            continue
        else:
            user = create_new_user_from_streaming(streaming_user)
            if user:
                UserAssociatedSystem.objects.create(userid=email, user=user, application=application)
                print user.email
