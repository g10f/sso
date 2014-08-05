from django.conf import settings as site_settings
from django.contrib.sites.models import get_current_site

import logging

log = logging.getLogger(__name__)


def get_base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def settings(request):
    
    return {'navigation_template': site_settings.SSO_CUSTOM.get('NAVIGATION_TEMPLATE', "include/_navigation.html"),
            'brand': site_settings.SSO_CUSTOM['BRAND'],
            'base_url': get_base_url(request),
            'stylesheet': site_settings.SSO_CUSTOM['STYLESHEET'],
            'stylesheet_less': site_settings.SSO_CUSTOM['SYLE_LESS'],
            'favicon': site_settings.SSO_CUSTOM['FAVICON']
            }
