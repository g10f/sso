from django.conf import settings as site_settings
from django.contrib.sites.shortcuts import get_current_site

import logging
from sso.auth.utils import get_device_classes

log = logging.getLogger(__name__)


def get_base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def settings(request):
    
    return {
        'brand': site_settings.SSO_BRAND,
        'base_url': get_base_url(request),
        'stylesheet': 'css/%(style)s-%(version)s.css' % {'style': site_settings.SSO_STYLE, 'version': site_settings.SSO_STYLE_VERSION},
        'stylesheet_less': 'less/%(style)s.less' % {'style': site_settings.SSO_STYLE},
        'less': site_settings.SSO_LESS,
        'favicon': site_settings.SSO_FAVICON,
        'sso_app_uuid': site_settings.SSO_APP_UUID,
        'registration_open': site_settings.REGISTRATION.get('OPEN', True),
        'device_classes': get_device_classes(),
        'email_management': site_settings.SSO_ORGANISATION_EMAIL_MANAGEMENT,
        'region_management': site_settings.SSO_REGION_MANAGEMENT,
        }
