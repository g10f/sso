# -*- coding: utf-8 -*-
from django.core.management.base import NoArgsCommand
from streaming.models import StreamingUser
from streaming.backends import add_streaming_user
from django.conf import settings
from sso.accounts.models import Application, UserAssociatedSystem, Role, ApplicationRole

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


def load_streaming_users():
    
    streaming_users = StreamingUser.objects.all()
    application = Application.objects.get_or_create(uuid=settings.STREAMING_UUID, defaults={'title': 'Streaming'})[0]
    
    role = Role.objects.get_or_create(name='User')[0]
    user_app_role = ApplicationRole.objects.get_or_create(application=application, role=role)[0]
    
    for streaming_user in streaming_users:
        email = streaming_user.email
        username = email[:28]
        password = streaming_user.password
        
        try:
            password = password.decode('base64')
        except Exception, e:
            print "error decoding password %s. %s" % (password, e)
            
        if UserAssociatedSystem.objects.filter(userid=email, application=application).exists():
            print 'user %s exists' % username
            continue

        is_center = True if (streaming_user.center == 'J') else False
        is_subscriber = True if (streaming_user.subscriber == 'J') else False

        add_streaming_user(username, email, password, is_center, is_subscriber, application, user_app_role)
