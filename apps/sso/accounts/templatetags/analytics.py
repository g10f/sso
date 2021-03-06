from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag("analytics/tracker.html")
def show_tracker(secure=False):
    """
    Output the analytics tracker code.
    """
    google = getattr(settings, 'ANALYTICS', {})
    if google:
        analytics_code = google.get('ANALYTICS_CODE')
        if analytics_code:
            return {"analytics_code": analytics_code}
    return {}
