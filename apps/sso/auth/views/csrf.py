import time

from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.middleware.csrf import REASON_NO_CSRF_COOKIE, REASON_NO_REFERER
from django.template import loader
from django.utils.translation import gettext as _

from sso.auth import SESSION_AUTH_DATE
from sso.auth.views import get_login_success_url

# The login and the 2-step verification rotate the CSRF token (auth_login). A form that is
# submitted a second time while the first, successful POST is still redirecting carries the old
# token and fails. The user is logged in by then, so continue where the first POST went.
# Only right after that login: an older session must not skip a login form, e.g. one that a
# client requested with prompt=login, which get_login_success_url removes from the next url.
# 15 s like the reset in static/js/single_submit.js: a click after that reset still continues.
DOUBLE_SUBMIT_MAX_SECONDS = 15


def is_double_submitted_login(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return False
    auth_date = request.session.get(SESSION_AUTH_DATE)
    if auth_date is None:
        return False
    return int(time.time()) - auth_date <= DOUBLE_SUBMIT_MAX_SECONDS


def csrf_failure(request, reason=''):
    """CSRF_FAILURE_VIEW"""
    if is_double_submitted_login(request):
        # resolver_match is set before the CSRF check runs (process_view)
        view_name = request.resolver_match.view_name if request.resolver_match else None
        if view_name == 'auth:login':
            return HttpResponseRedirect(get_login_success_url(request, request.user, mfa_check=True))
        if view_name == 'auth:token':
            # the mfa setup was already checked when the password was entered
            return HttpResponseRedirect(get_login_success_url(request, request.user, mfa_check=False))

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
