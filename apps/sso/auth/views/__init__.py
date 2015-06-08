import urllib
import logging
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.conf import settings

from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic.edit import FormView
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.core import signing
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _

from sso.auth.forms import EmailAuthenticationForm, AuthenticationTokenForm
from sso.auth.models import Device
from sso.auth.utils import get_safe_login_redirect_url, get_request_param, get_device_classes
from sso.oauth2.models import get_oauth2_cancel_url
from sso.auth import auth_login
from throttle.decorators import throttle

SALT = 'sso.auth.views.LoginView'

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

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(LoginView, self).get_initial()
        initial['remember_me'] = not self.request.session.get_expire_at_browser_close()
        return initial

    def form_valid(self, form):
        user = form.get_user()
        redirect_url = get_safe_login_redirect_url(self.request)

        # if 2-nd factor available, send token
        device = is_otp_login(user, self.is_otp)
        expiry = settings.SESSION_COOKIE_AGE if form.cleaned_data.get('remember_me', False) else 0

        if device:
            try:
                challenge = device.generate_challenge()
                user_data = signing.dumps({'user_id': user.pk, 'backend': user.backend, 'expiry': expiry}, salt=SALT)
                logger.debug(challenge)
                query_string = {REDIRECT_FIELD_NAME: redirect_url}
                display = self.request.GET.get('display')
                if display:
                    query_string['display'] = display

                self.success_url = "%s?%s" % (reverse('auth:token', kwargs={'user_data': user_data, 'device_id': device.id}), urllib.urlencode(query_string))
            except StandardError, e:
                messages.error(self.request, _('Device error, select another device. (%(error)s)') % {'error': e.message})
                return self.render_to_response(self.get_context_data(form=form))

        else:
            self.success_url = redirect_url
            auth_login(self.request, user, expiry)

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
    expiry = 0

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, *args, **kwargs):
        return super(TokenView, self).dispatch(*args, **kwargs)

    def get_form_class(self):
        state = signing.loads(self.kwargs['user_data'], salt=SALT)
        self.user = get_user_model().objects.get(pk=state['user_id'])
        self.device = Device.objects.get(user=self.user, pk=self.kwargs['device_id'])
        return self.device.login_form_class

    def get_template_names(self):
        try:
            return self.device.login_form_templates
        except StandardError:
            return super(TokenView, self).get_template_names()

    def get_form_kwargs(self):
        kwargs = super(TokenView, self).get_form_kwargs()

        state = signing.loads(self.kwargs['user_data'], salt=SALT)
        self.expiry = state['expiry']
        self.user = get_user_model().objects.get(pk=state['user_id'])
        self.user.backend = state['backend']
        self.device = Device.objects.get(user=self.user, pk=self.kwargs['device_id'])

        kwargs['user'] = self.user
        kwargs['device'] = self.device
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('resend_token'):
            state = signing.loads(self.kwargs['user_data'], salt=SALT)
            device = Device.objects.get(user_id=state['user_id'], pk=self.kwargs['device_id'])
            challenge = device.generate_challenge()
            messages.add_message(self.request, level=messages.INFO, message=challenge, fail_silently=True)
            return redirect("%s?%s" % (self.request.path, self.request.GET.urlencode()))

        return super(TokenView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Adds user's default and backup OTP devices to the context.
        """
        context = super(TokenView, self).get_context_data(**kwargs)

        device_classes = get_device_classes()
        other_devices = []
        for device_class in device_classes:
            for device in device_class.objects.filter(user=self.user).exclude(device_ptr_id=self.device.id).prefetch_related('device_ptr'):
                device_info = {
                    'device': device,
                    'url': "%s?%s" % (reverse('auth:token', kwargs={'user_data': self.kwargs['user_data'], 'device_id': device.id}), self.request.GET.urlencode())
                }
                other_devices.append(device_info)

        context['challenges'] = self.device.challenges
        context['other_devices'] = other_devices
        context['device'] = self.device
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context

    def form_valid(self, form):
        redirect_url = get_safe_login_redirect_url(self.request)
        auth_login(self.request, form.user, self.expiry, self.device.id)

        self.success_url = redirect_url
        return super(TokenView, self).form_valid(form)
