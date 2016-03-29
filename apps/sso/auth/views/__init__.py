import urllib
import logging

from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic.edit import FormView
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model, BACKEND_SESSION_KEY
from django.core import signing
from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _
from throttle.decorators import throttle
from sso.auth.forms import EmailAuthenticationForm, AuthenticationTokenForm
from sso.auth.models import Device
from sso.auth.utils import get_safe_login_redirect_url, get_request_param, get_device_classes
from sso.oauth2.models import get_oauth2_cancel_url
from sso.auth import is_otp_login, auth_login

SALT = 'sso.auth.views.LoginView'
TWO_FACTOR_PARAM = 'two_factor'

logger = logging.getLogger(__name__)


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy('home')
    is_two_factor_required = False

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get_token_url(user_id, expiry, redirect_url, backend, display, device_id):
        user_data = signing.dumps({'user_id': user_id, 'backend': backend, 'expiry': expiry}, salt=SALT)
        query_string = {REDIRECT_FIELD_NAME: redirect_url}
        if display:
            query_string['display'] = display

        return "%s?%s" % (reverse('auth:token', kwargs={'user_data': user_data, 'device_id': device_id}), urllib.urlencode(query_string))

    def get(self, request, *args, **kwargs):
        self.is_two_factor_required = get_request_param(request, 'two_factor', False) is not False
        user = request.user
        if self.is_two_factor_required and user.is_authenticated() and user.device_set.filter(confirmed=True).exists():
            session = request.session
            redirect_url = get_safe_login_redirect_url(request)
            expiry = 0 if session.get_expire_at_browser_close() else settings.SESSION_COOKIE_AGE
            backend = session[BACKEND_SESSION_KEY]
            device = is_otp_login(user, self.is_two_factor_required)
            device.generate_challenge()
            display = request.GET.get('display')
            token_url = self.get_token_url(user.id, expiry, redirect_url, backend, display, device.id)
            return redirect(token_url)

        return super(LoginView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = super(LoginView, self).get_initial()
        initial['remember_me'] = not self.request.session.get_expire_at_browser_close()
        return initial

    def form_valid(self, form):
        user = form.get_user()
        redirect_url = get_safe_login_redirect_url(self.request)

        # if 2-nd factor available, send token
        self.is_two_factor_required = get_request_param(self.request, TWO_FACTOR_PARAM, False) is not False
        device = is_otp_login(user, self.is_two_factor_required)
        expiry = settings.SESSION_COOKIE_AGE if form.cleaned_data.get('remember_me', False) else 0

        if device:
            try:
                device.generate_challenge()
                display = self.request.GET.get('display')
                self.success_url = self.get_token_url(user.id, expiry, redirect_url, user.backend, display, device.id)
            except StandardError as e:
                messages.error(self.request, _('Device error, select another device. (%(error)s)') % {'error': e.message})
                return self.render_to_response(self.get_context_data(form=form))

        else:
            self.success_url = redirect_url
            user._auth_session_expiry = expiry  # used to update the session in auth_login

            auth_login(self.request, user)

        return super(LoginView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['site_name'] = settings.SSO_SITE_NAME
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context


class TokenView(FormView):
    template_name = 'auth/token.html'
    form_class = AuthenticationTokenForm
    success_url = reverse_lazy('home')
    user = None
    device = None
    expiry = 0
    challenges = None

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, *args, **kwargs):
        return super(TokenView, self).dispatch(*args, **kwargs)

    def get_form_class(self):
        state = signing.loads(self.kwargs['user_data'], salt=SALT)
        self.expiry = state['expiry']
        self.user = get_user_model().objects.get(pk=state['user_id'])
        self.user.backend = state['backend']
        self.device = Device.objects.get(user=self.user, pk=self.kwargs['device_id'])
        return self.device.login_form_class

    def get_template_names(self):
        try:
            return self.device.login_form_templates
        except StandardError:
            return super(TokenView, self).get_template_names()

    def get_form_kwargs(self):
        kwargs = super(TokenView, self).get_form_kwargs()
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

        context['other_devices'] = other_devices
        context['device'] = self.device
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context

    def get_initial(self):
        initial = super(TokenView, self).get_initial()
        if self.request.method == 'GET':
            initial.update({'challenges': self.device.challenges()})
        else:
            initial.update({'challenges': self.request.POST.get('challenges')})

        return initial

    def form_valid(self, form):
        redirect_url = get_safe_login_redirect_url(self.request)
        user = form.user
        user._auth_device_id = self.device.id
        user._auth_session_expiry = self.expiry
        auth_login(self.request, form.user)
        self.success_url = redirect_url
        return super(TokenView, self).form_valid(form)
