import logging
from functools import cache
from importlib import import_module

from django.conf import settings as site_settings
from sso.sidebar import sidebar
from sso.utils.url import get_base_url
from sso import __version__
log = logging.getLogger(__name__)


@cache
def site_version():
    """The version of the deployed image, shown in the footer.

    A theme image (FROM this image) names its package in the setting SSO_THEME; its __version__ is the
    version of the theme release (X.Y.Z, or X.Y.Z.N for a change of the theme alone). Without a theme,
    or a theme without __version__, it is the version of this project.
    """
    theme = getattr(site_settings, 'SSO_THEME', None)
    if theme:
        theme_version = getattr(import_module(theme), '__version__', None)
        if theme_version:
            return theme_version
    return __version__


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
        'version': site_version()
    }
