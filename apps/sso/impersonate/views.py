from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, load_backend
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ImproperlyConfigured
from django.forms import forms
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from sso.auth import auth_login
from sso.auth.decorators import admin_login_required
from sso.forms.helpers import log_change


@admin_login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def impersonate_user(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    if request.method == 'POST':
        # Find a suitable backend.
        if not hasattr(user, "backend"):
            for backend in settings.AUTHENTICATION_BACKENDS:
                if not hasattr(load_backend(backend), "get_user"):
                    continue
                if user == load_backend(backend).get_user(user.uuid):
                    user.backend = backend
                    break
            else:
                raise ImproperlyConfigured("Could not found an appropriate authentication backend")

        form = forms.Form(request.POST)
        if form.is_valid():
            try:
                original_user = request.user
                auth_login(request, user)
                messages.warning(request, _("You are logged in as %s ." % user.username))
                # Add admin log entry
                change_message = "User {0} logged in as {1}.".format(original_user, user)
                log_change(request, user, change_message)
                return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
            except Exception as e:
                message = _("There was an error %s") % e
                messages.error(request, message)

    return redirect(request.headers.get('Referer'))
