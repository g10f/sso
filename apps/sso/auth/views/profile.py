import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse_lazy, reverse
from django.views.generic import FormView, UpdateView
from sso.auth.forms.profile import TOTPDeviceForm, ProfileForm, AddU2FForm, DeviceUpdateForm
from sso.auth.models import U2FDevice, Device, Profile
from sso.auth.utils import random_hex

logger = logging.getLogger(__name__)


class AddU2FView(LoginRequiredMixin, FormView):
    template_name = 'sso_auth/u2f/add_device.html'
    form_class = AddU2FForm
    success_url = reverse_lazy('auth:mfa-detail')
    u2f_request = None

    def get(self, request, *args, **kwargs):
        self.u2f_request = U2FDevice.register_begin(self.request)
        return super().get(request, *args, **kwargs)

    def get_origin(self):
        request = self.request
        return '{scheme}://{host}'.format(scheme=request.scheme, host=request.get_host())

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs['u2f_request'] = json.dumps(self.u2f_request)
        kwargs['device_cls'] = U2FDevice
        kwargs['cancel_url'] = reverse('auth:mfa-detail')
        return kwargs

    def form_valid(self, form):
        name = form.cleaned_data['name']
        response_data = form.cleaned_data.get('u2f_response')
        state_data = form.cleaned_data.get('state')
        user = self.request.user
        device = U2FDevice.register_complete(name, response_data, state_data, user)
        if not hasattr(user, 'sso_auth_profile'):
            Profile.objects.create(user=user, default_device_id=device.device_id, is_otp_enabled=True)

        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        if self.u2f_request is not None:
            initial.update({'u2f_request': json.dumps(self.u2f_request)})
        return initial


class DetailView(LoginRequiredMixin, FormView):
    """
    View used by users for managing two-factor configuration.

    This view shows whether two-factor has been configured for the user's
    account. If two-factor is enabled, it also lists the primary verification
    method and backup verification methods.
    """
    template_name = 'sso_auth/detail.html'
    form_class = ProfileForm
    success_url = reverse_lazy('auth:mfa-detail')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class AddTOTP(LoginRequiredMixin, FormView):
    template_name = 'sso_auth/totp/add_device.html'
    form_class = TOTPDeviceForm
    success_url = reverse_lazy('auth:mfa-detail')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initial.update({'key': random_hex(20).decode('ascii')})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'issuer': get_current_site(self.request).name
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    form_class = DeviceUpdateForm
    model = Device
    success_url = reverse_lazy('auth:mfa-detail')
