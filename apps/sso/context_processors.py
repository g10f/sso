from django.conf import settings as site_settings
from django.contrib.sites.models import get_current_site

import logging

log = logging.getLogger(__name__)


def get_base_url(request):
    return '%s://%s' % ('https' if request.is_secure() else 'http', get_current_site(request).domain)


def settings(request):
    
    return {'brand': site_settings.BRAND,
            'app_uuid': site_settings.APP_UUID,
            'base_url': get_base_url(request),
            'stylesheet': site_settings.STYLESHEET
            }
