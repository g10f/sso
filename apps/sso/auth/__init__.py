import time
from django.contrib.auth import login

default_app_config = 'sso.auth.apps.AuthConfig'

SESSION_AUTH_DATE = '_auth_date'
DEVICE_KEY = '_auth_device'

def auth_login(request, user, expiry=0, device_id=None):
    #  insert the authentication date and authentication device into the session
    login(request, user)
    request.session.set_expiry(expiry)
    request.session[SESSION_AUTH_DATE] = long(time.time())
    if device_id:
        request.session[DEVICE_KEY] = device_id
