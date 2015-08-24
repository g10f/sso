from importlib import import_module

from django.test.client import Client
from django.apps import apps
from django.conf import settings
from django.http import HttpRequest


class SSOClient(Client):
    def login(self, **credentials):
        """
        instead of using django.contrib.auth.login we are using
        auth_login because we use the uuid and some special keys
        """
        from django.contrib.auth import authenticate
        from sso.auth import auth_login

        user = authenticate(**credentials)
        if (user and user.is_active and
                apps.is_installed('django.contrib.sessions')):
            engine = import_module(settings.SESSION_ENGINE)

            # Create a fake request to store login details.
            request = HttpRequest()

            if self.session:
                request.session = self.session
            else:
                request.session = engine.SessionStore()
            # changed from django.contrib.auth.login to auth_login
            auth_login(request, user)

            # Save the session values.
            request.session.save()

            # Set the cookie to represent the session.
            session_cookie = settings.SESSION_COOKIE_NAME
            self.cookies[session_cookie] = request.session.session_key
            cookie_data = {
                'max-age': None,
                'path': '/',
                'domain': settings.SESSION_COOKIE_DOMAIN,
                'secure': settings.SESSION_COOKIE_SECURE or None,
                'expires': None,
            }
            self.cookies[session_cookie].update(cookie_data)

            return True
        else:
            return False
