import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from sso.accounts.models import User
from sso.oauth2.models import allowed_hosts
from sso.signals import user_admins
from sso.utils.url import get_safe_redirect_uri, update_url
from .forms import AccountUpgradeForm

logger = logging.getLogger(__name__)


class AccountExtendAccessDoneView(TemplateView):
    template_name = 'access_requests/extend_access_thanks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['redirect_uri'] = get_safe_redirect_uri(self.request, allowed_hosts())
        context['site_name'] = settings.SSO_SITE_NAME
        return context


class AccountExtendAccessView(FormView):
    template_name = 'access_requests/extend_access.html'
    form_class = AccountUpgradeForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        return update_url(reverse('extend_access_thanks'), {'redirect_uri': redirect_uri})

    def get_form_kwargs(self):
        """
        add user to form kwargs for filtering the adminregions
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        redirect_uri = get_safe_redirect_uri(self.request, allowed_hosts())
        # enable brand specific modification
        admins = set()
        user_admins.send_robust(sender=self.__class__, organisations=user.organisations.all(), admins=admins)
        context.update({'site_name': settings.SSO_SITE_NAME, 'max_file_size': User.MAX_PICTURE_SIZE,
                        'admins': admins, 'redirect_uri': redirect_uri})
        return context

    def form_valid(self, form):
        user = self.request.user
        admins = set()
        user_admins.send_robust(sender=self.__class__, organisations=user.organisations.all(), admins=admins)
        form.save()
        form.send_email(admins)
        return super().form_valid(form)
