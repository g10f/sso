from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.middleware.csrf import REASON_NO_CSRF_COOKIE, REASON_NO_REFERER
from django.template import loader
from django.urls import Resolver404, resolve
from django.utils.translation import gettext as _

from sso.auth.views import get_login_success_url

# The login and the 2-step verification rotate the CSRF token (auth_login). A form that is
# submitted a second time while the first, successful POST is still redirecting carries the old
# token and fails. The user is logged in by then, so continue where the first POST went.
LOGIN_VIEWS = {'auth:login': True, 'auth:token': False}  # view name: check the mfa setup


def csrf_failure(request, reason=''):
    """CSRF_FAILURE_VIEW"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            view_name = resolve(request.path_info).view_name
        except Resolver404:
            view_name = None
        if view_name in LOGIN_VIEWS:
            return HttpResponseRedirect(get_login_success_url(request, request.user, mfa_check=LOGIN_VIEWS[view_name]))

    # django.views.csrf.csrf_failure renders a custom 403_csrf.html with the request only, so the
    # template gets its context here (same messages, so that Django's translations apply)
    context = {
        'title': _('Forbidden'),
        'main': _('CSRF verification failed. Request aborted.'),
        'no_referer': reason == REASON_NO_REFERER,
        'no_referer1': _(
            'You are seeing this message because this HTTPS site requires a '
            '“Referer header” to be sent by your web browser, but none was '
            'sent. This header is required for security reasons, to ensure '
            'that your browser is not being hijacked by third parties.'),
        'no_referer2': _(
            'If you have configured your browser to disable “Referer” headers, '
            'please re-enable them, at least for this site, or for HTTPS '
            'connections, or for “same-origin” requests.'),
        'no_cookie': reason == REASON_NO_CSRF_COOKIE,
        'no_cookie1': _(
            'You are seeing this message because this site requires a CSRF '
            'cookie when submitting forms. This cookie is required for '
            'security reasons, to ensure that your browser is not being '
            'hijacked by third parties.'),
        'no_cookie2': _(
            'If you have configured your browser to disable cookies, please '
            're-enable them, at least for this site, or for “same-origin” '
            'requests.'),
        # with the query string: the login form needs its next parameter to return to the client
        'retry_url': request.get_full_path(),
    }
    body = loader.render_to_string('403_csrf.html', context, request=request)
    return HttpResponseForbidden(body)
