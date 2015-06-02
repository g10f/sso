import urllib
import logging
from django.contrib import messages
from django.views.generic.edit import FormView
from django.conf import settings


# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import (
    REDIRECT_FIELD_NAME, login as auth_login,
    get_user_model)
from django.core import signing
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _

from sso.auth.forms import EmailAuthenticationForm, AuthenticationTokenForm
from sso.auth.models import Device
from sso.auth.utils import get_safe_login_redirect_url, get_request_param
from sso.oauth2.models import get_oauth2_cancel_url

SALT = 'sso.auth.views.LoginView'
DEVICE_KEY = '_auth_device'
# ACR = '_auth_acr'

logger = logging.getLogger(__name__)

def is_otp_login(user, is_otp):
    if hasattr(user, 'sso_auth_profile'):
        profile = user.sso_auth_profile
        if (profile.default_device and profile.is_otp_enabled) or \
                (profile.default_device and is_otp):
            return profile.default_device

    return None


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy('home')
    is_otp = False

    def form_valid(self, form):
        user = form.get_user()
        redirect_url = get_safe_login_redirect_url(self.request)

        # if 2-nd factor available, send token
        device = is_otp_login(user, self.is_otp)
        if device:
            try:
                challenge = device.generate_challenge()
                user_data = signing.dumps({'user_id': user.pk, 'backend': user.backend, 'device_id': device.id}, salt=SALT)
                logger.debug(challenge)
                query_string = urllib.urlencode({REDIRECT_FIELD_NAME: redirect_url})
                self.success_url = "%s?%s" % (reverse('auth:token', kwargs={'user_data': user_data}), query_string)
            except StandardError, e:
                messages.error(self.request, _('Device error, select another device. (%(error)s)') % {'error': e.message})
                return self.render_to_response(self.get_context_data(form=form))

        else:
            self.success_url = redirect_url
            auth_login(self.request, user)

        return super(LoginView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context


class TokenView(FormView):
    template_name = 'auth/token.html'
    form_class = AuthenticationTokenForm
    success_url = reverse_lazy('home')
    user = None
    device = None

    def get_form_kwargs(self):
        kwargs = super(TokenView, self).get_form_kwargs()

        state = signing.loads(self.kwargs['user_data'], salt=SALT)
        self.user = get_user_model().objects.get(pk=state['user_id'])
        self.user.backend = state['backend']
        self.device = Device.objects.get(user=self.user, pk=state['device_id'])
        kwargs['user'] = self.user
        kwargs['device'] = self.device
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Adds user's default and backup OTP devices to the context.
        """
        context = super(TokenView, self).get_context_data(**kwargs)
        context['device'] = self.device
        context['cancel_url'] = settings.LOGOUT_URL
        return context

    def form_valid(self, form):
        redirect_url = get_safe_login_redirect_url(self.request)
        auth_login(self.request, form.user)
        self.request.session[DEVICE_KEY] = self.device.id

        self.success_url = redirect_url
        return super(TokenView, self).form_valid(form)
