from django.conf import settings as site_settings
from django.contrib.sites.shortcuts import get_current_site

import logging

log = logging.getLogger(__name__)


def get_base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def settings(request):
    
    return {'navigation_template': site_settings.SSO_NAVIGATION_TEMPLATE,
            'brand': site_settings.SSO_BRAND,
            'base_url': get_base_url(request),
            'stylesheet': site_settings.SSO_STYLESHEET,
            'stylesheet_less': site_settings.SSO_SYLE_LESS,
            'favicon': site_settings.SSO_FAVICON
            }
