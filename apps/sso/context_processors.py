import logging

from django.apps import apps

from django.conf import settings as site_settings
from sso.auth.utils import get_device_classes
from sso.utils.url import get_base_url

log = logging.getLogger(__name__)


def settings(request):
    return {
        'brand': site_settings.SSO_BRAND,
        'base_url': get_base_url(request),
        'stylesheet': 'css/%(style)s-%(version)s.css' % {'style': site_settings.SSO_STYLE,
                                                         'version': site_settings.SSO_STYLE_VERSION},
        'stylesheet_less': 'less/%(style)s.less' % {'style': site_settings.SSO_STYLE},
        'sso_app_uuid': site_settings.SSO_APP_UUID,
        'registration_open': site_settings.REGISTRATION.get('OPEN', True),
        'device_classes': get_device_classes(),
        'admin_only_2f': site_settings.SSO_ADMIN_ONLY_2F,
        'email_management': site_settings.SSO_ORGANISATION_EMAIL_MANAGEMENT,
        'region_management': site_settings.SSO_REGION_MANAGEMENT,
        'country_management': site_settings.SSO_COUNTRY_MANAGEMENT,
        'data_protection_uri': site_settings.SSO_DATA_PROTECTION_URI,
        'sso_access_requests_is_installed': apps.is_installed('sso.access_requests')
    }
