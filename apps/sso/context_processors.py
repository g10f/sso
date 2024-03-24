import logging

from django.conf import settings as site_settings
from sso.sidebar import sidebar
from sso.utils.url import get_base_url
from sso import __version__
log = logging.getLogger(__name__)


def settings(request):
    return {
        'enable_plausible': site_settings.SSO_ENABLE_PLAUSIBLE,
        'domain': site_settings.SSO_DOMAIN,
        'brand': site_settings.SSO_BRAND,
        'base_url': get_base_url(request),
        # 'stylesheet': 'css/%(style)s-%(version)s.css' % {'style': site_settings.SSO_STYLE, 'version': site_settings.SSO_STYLE_VERSION},
        'sso_app_uuid': site_settings.SSO_APP_UUID,
        'registration_open': site_settings.REGISTRATION.get('OPEN', True),
        'data_protection_uri': site_settings.SSO_DATA_PROTECTION_URI,
        'sso_region_management': site_settings.SSO_REGION_MANAGEMENT,
        'sidebar': sidebar(request),
        'sso_style': site_settings.SSO_STYLE,
        'default_theme': site_settings.SSO_DEFAULT_THEME,
        'version': __version__
    }
