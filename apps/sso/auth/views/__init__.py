import logging
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, logout as auth_logout
from django.contrib.auth import get_user_model, BACKEND_SESSION_KEY
from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView
from sso.auth import is_otp_login, auth_login
from sso.auth.forms import EmailAuthenticationForm, AuthenticationTokenForm
from sso.auth.models import Device
from sso.auth.utils import get_safe_login_redirect_url, get_request_param, get_device_classes_for_user, should_use_mfa
from sso.middleware import revision_exempt
from sso.oauth2.crypt import loads_jwt
from sso.oauth2.models import allowed_hosts, post_logout_redirect_uris, Client
from sso.oauth2.models import get_oauth2_cancel_url
from sso.utils.http import HttpPostLogoutRedirect
from sso.utils.url import get_safe_redirect_uri, REDIRECT_URI_FIELD_NAME, update_url, remove_value_from_url_param
from throttle.decorators import throttle

SALT = 'sso.auth.views.LoginView'
TWO_FACTOR_PARAM = 'two_factor'
OIDC_LOGOUT_REDIRECT_FIELD_NAME = 'post_logout_redirect_uri'
OIDC_ID_TOKEN_HINT = 'id_token_hint'
OIDC_STATE = 'state'

logger = logging.getLogger(__name__)


def get_token_url(user_id, expiry, redirect_url, backend, display, device_id):
    user_data = signing.dumps({'user_id': user_id, 'backend': backend, 'expiry': expiry}, salt=SALT)
    query_string = {REDIRECT_FIELD_NAME: redirect_url}
    if display:
        query_string['display'] = display

    return "%s?%s" % (reverse('auth:token', kwargs={'user_data': user_data, 'device_id': device_id}),
                      urlencode(query_string))


class LoginView(FormView):
    template_name = 'sso_auth/login.html'
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy('home')
    is_two_factor_required = False

    @method_decorator(revision_exempt)
    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.is_two_factor_required = get_request_param(request, 'two_factor', False) is not False
        user = request.user
        if self.is_two_factor_required and user.is_authenticated and user.device_set.filter(confirmed=True).exists():
            session = request.session
            redirect_url = get_safe_login_redirect_url(request)
            expiry = 0 if session.get_expire_at_browser_close() else settings.SESSION_COOKIE_AGE
            backend = session[BACKEND_SESSION_KEY]
            device_cls = is_otp_login(user, self.is_two_factor_required)
            display = request.GET.get('display')
            token_url = get_token_url(user.id, expiry, redirect_url, backend, display, device_cls.get_device_id())
            return redirect(token_url)

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['remember_me'] = not self.request.session.get_expire_at_browser_close()
        return initial

    def form_valid(self, form):
        user = form.get_user()
        redirect_url = get_safe_login_redirect_url(self.request)

        # if 2-nd factor available, send token
        self.is_two_factor_required = get_request_param(self.request, TWO_FACTOR_PARAM, 'False').lower() in ('true', '1', 't')
        expiry = settings.SESSION_COOKIE_AGE if form.cleaned_data.get('remember_me', False) else 0
        device_cls = is_otp_login(user, self.is_two_factor_required)
        display = self.request.GET.get('display')

        if device_cls:
            try:
                self.success_url = get_token_url(user.id, expiry, redirect_url, user.backend, display, device_cls.get_device_id())
            except Exception as e:
                messages.error(
                    self.request,
                    _('Device error, select another device. (%(error)s)') % {'error': force_str(e)})
                return self.render_to_response(self.get_context_data(form=form))

        else:
            # remove the prompt login param, cause login was done here
            success_url = remove_value_from_url_param(redirect_url, 'prompt', 'login')

            if should_use_mfa(user) and display not in ['popup']:
                query_string = {REDIRECT_FIELD_NAME: success_url}
                self.success_url = "%s?%s" % (reverse('auth:mfa-detail'), urlencode(query_string))
            else:
                self.success_url = success_url

            user._auth_session_expiry = expiry  # used to update the session in auth_login
            auth_login(self.request, user)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['site_name'] = settings.SSO_SITE_NAME
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context


class TokenView(FormView):
    template_name = 'sso_auth/token.html'
    form_class = AuthenticationTokenForm
    success_url = reverse_lazy('home')
    user = None
    device_cls = None
    expiry = 0
    challenges = None
    error_messages = {
        'signature_expired': _("The login process took too long. Please try again."),
    }

    @method_decorator(revision_exempt)
    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    @method_decorator(throttle(duration=30, max_calls=12))
    def dispatch(self, *args, **kwargs):
        try:
            state = signing.loads(self.kwargs['user_data'], salt=SALT, max_age=settings.SSO_LOGIN_MAX_AGE)
            self.expiry = state['expiry']
            self.user = get_user_model().objects.get(pk=state['user_id'])
            self.user.backend = state['backend']
        except signing.SignatureExpired as e:
            logger.info(e)
            message = self.error_messages['signature_expired']
            messages.add_message(self.request, level=messages.ERROR, message=message, fail_silently=True)
            # redirect to login page with correct next url
            return redirect(get_safe_login_redirect_url(self.request))

        return super().dispatch(*args, **kwargs)

    def get_form_class(self):
        self.device_cls = Device.get_subclass(self.kwargs['device_id'])
        return self.device_cls.login_form_class()

    def get_template_names(self):
        try:
            return self.device_cls.login_form_templates()
        except RuntimeError:
            return super().get_template_names()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def post(self, request, *args, **kwargs):
        if request.POST.get('resend_token'):
            return redirect("%s?%s" % (self.request.path, self.request.GET.urlencode()))

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Adds user's default and backup OTP devices to the context.
        """
        context = super().get_context_data(**kwargs)

        device_classes = get_device_classes_for_user(self.user)
        other_devices = []
        for device_cls in filter(lambda d: d != self.device_cls, device_classes):
            device_info = {
                'name': device_cls.default_name(),
                'url': "%s?%s" % (
                    reverse('auth:token', kwargs={'user_data': self.kwargs['user_data'], 'device_id': device_cls.get_device_id()}),
                    self.request.GET.urlencode())
            }
            other_devices.append(device_info)

        context['other_devices'] = other_devices
        context['device_cls'] = self.device_cls
        redirect_url = get_safe_login_redirect_url(self.request)
        context['cancel_url'] = get_oauth2_cancel_url(redirect_url)
        context['display'] = get_request_param(self.request, 'display', 'page')
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.request.method == 'GET':
            initial.update({'challenges': self.device_cls.challenges(self.user)})
        else:
            initial.update({'challenges': self.request.POST.get('challenges')})

        return initial

    def form_valid(self, form):
        redirect_url = get_safe_login_redirect_url(self.request)
        user = form.user
        user._auth_device_id = form.device.id
        user._auth_session_expiry = self.expiry
        auth_login(self.request, form.user)
        # remove the prompt login param, cause login was done here
        self.success_url = remove_value_from_url_param(redirect_url, 'prompt', 'login')
        return super().form_valid(form)


@never_cache
def logout(request, next_page=None,
           template_name='sso_auth/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    see http://openid.net/specs/openid-connect-session-1_0.html#RPLogout
    """
    # save the user
    user = request.user
    auth_logout(request)
    # 1. check if we have a post_logout_redirect_uri which is registered
    redirect_to = settings.LOGIN_REDIRECT_URL
    redirect_uri = get_request_param(request, OIDC_LOGOUT_REDIRECT_FIELD_NAME)
    allowed_schemes = ['http', 'https']
    if redirect_uri:
        id_token = get_request_param(request, OIDC_ID_TOKEN_HINT)
        if id_token:
            # token maybe expired
            data = loads_jwt(id_token, options={"verify_exp": False, "verify_aud": False})
            if user.is_anonymous or user.uuid == UUID(data['sub']):
                client = Client.objects.get(uuid=data['aud'])
                if redirect_uri in client.post_logout_redirect_uris.split():
                    # allow unsafe schemes
                    redirect_to = redirect_uri
                    allowed_schemes = None
        else:
            # if no OIDC_ID_TOKEN_HINT is there, allow only safe schemes
            if redirect_uri in post_logout_redirect_uris():
                redirect_to = redirect_uri
        redirect_to = update_url(redirect_to, {OIDC_STATE: get_request_param(request, OIDC_STATE)})
        return HttpPostLogoutRedirect(redirect_to=redirect_to, allowed_schemes=allowed_schemes)
    else:
        # deprecated logic
        redirect_uris = [redirect_field_name, REDIRECT_URI_FIELD_NAME, OIDC_LOGOUT_REDIRECT_FIELD_NAME]
        redirect_to = get_safe_redirect_uri(request, allowed_hosts(), redirect_uris)
        if redirect_to:
            return HttpPostLogoutRedirect(redirect_to=redirect_to, allowed_schemes=['http', 'https'])

    if next_page is None:
        current_site = get_current_site(request)
        site_name = settings.SSO_SITE_NAME
        context = {
            'site': current_site,
            'site_name': site_name,
            'title': _('Logged out')
        }
        if extra_context is not None:
            context.update(extra_context)
        if current_app is not None:
            request.current_app = current_app
        return TemplateResponse(request, template_name, context)
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)
