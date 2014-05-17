from django.template import Context
from django.utils.translation import ugettext as _
from django.shortcuts import render


def csrf_failure(request, reason="", template='csrf_failure.html'):
    from django.middleware.csrf import REASON_NO_REFERER, REASON_NO_CSRF_COOKIE
    c = Context({
        'title': _("Forbidden"),
        'main': _("CSRF verification failed. Request aborted."),
        'reason': reason,
        'no_referer': reason == REASON_NO_REFERER,
        'no_cookie': reason == REASON_NO_CSRF_COOKIE,
    })
    return render(request, template, c)
