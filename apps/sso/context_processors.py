import logging

from django.conf import settings as site_settings
from sso.sidebar import sidebar
from sso.utils.url import get_base_url

log = logging.getLogger(__name__)


def settings(request):
    return {
        'brand': site_settings.SSO_BRAND,
        'base_url': get_base_url(request),
        'stylesheet': 'css/%(style)s-%(version)s.css' % {'style': site_settings.SSO_STYLE, 'version': site_settings.SSO_STYLE_VERSION},
        'stylesheet_less': 'less/%(style)s.less' % {'style': site_settings.SSO_STYLE},
        'sso_app_uuid': site_settings.SSO_APP_UUID,
        'registration_open': site_settings.REGISTRATION.get('OPEN', True),
        'data_protection_uri': site_settings.SSO_DATA_PROTECTION_URI,
        'sidebar': sidebar(request)
    }
