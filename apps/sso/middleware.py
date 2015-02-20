# -*- coding: utf-8 -*-
import time
from django.conf import settings
from django.contrib import auth


class CookieProlongationMiddleware(object):
    """
    We don't want to save the session with every request, because this creates a changed cookie
    which is bad for caching.
    
    Otherwise the login should be prolongated if the user is active.
    The solution is to save the cookie after half of the SESSION_COOKIE_AGE.
    """
    
    def process_response(self, request, response):
        try:
            session = request.session
        except AttributeError:
            # CommonMiddleware returns HttpResponsePermanentRedirect in cases when to request url have been added 'www' or 
            # trailing '/' (APPEND_SLASH and PREPEND_WWW in settings). In such case django stops looking through middleware list 
            # for process_request methods and begins to run process_response methods.
            return response
        
        if (settings.SESSION_ENGINE in ['django.contrib.sessions.backends.signed_cookies', 'sso.sessions.backends']) \
                and not settings.SESSION_SAVE_EVERY_REQUEST \
                and (auth.SESSION_KEY in session):
            last_modified = session.get('last_modified')
            now = int(time.time())
            
            if not last_modified or ((now - last_modified) > settings.SESSION_COOKIE_AGE / 2):
                session['last_modified'] = now

            """
            iat = session.get('iat')
            exp = session.get('exp')
            now = int(time.time())

            if not iat or (now > (iat + exp) / 2):
                session['iat'] = now
            """

        return response
