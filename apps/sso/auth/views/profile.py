import json

from u2flib_server import u2f

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView
from sso.auth.forms.profile import TOTPDeviceForm, ProfileForm, AddU2FForm, DeviceUpdateForm
from sso.auth.models import U2FDevice, Profile, Device
from sso.auth.utils import default_device, random_hex, get_device_classes


class AddU2FView(LoginRequiredMixin, FormView):
    template_name = 'sso_auth/u2f/add_device.html'
    form_class = AddU2FForm
    success_url = reverse_lazy('auth:mfa-detail')
    u2f_request = None

    def get(self, request, *args, **kwargs):
        u2f_devices = U2FDevice.objects.filter(user=self.request.user, confirmed=True)
        devices = [d.to_json() for d in u2f_devices]
        self.u2f_request = u2f.begin_registration(app_id=self.get_origin(), registered_keys=devices).data_for_client
        return super().get(request, *args, **kwargs)

    def get_origin(self):
        request = self.request
        return '{scheme}://{host}'.format(scheme=request.scheme, host=request.get_host())

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        kwargs['u2f_request'] = json.dumps(self.u2f_request)

        return kwargs

    def form_valid(self, form):
        u2f_response = form.cleaned_data['u2f_response']
        u2f_request = form.cleaned_data['u2f_request']
        name = form.cleaned_data['name']
        device, attestation_cert = u2f.complete_registration(u2f_request, u2f_response)
        device = U2FDevice.objects.create(name=name, user=self.request.user, public_key=device['publicKey'], key_handle=device['keyHandle'],
                                          app_id=device['appId'], version=device['version'], confirmed=True)

        if not hasattr(self.request.user, 'sso_auth_profile'):
            Profile.objects.create(user=self.request.user, default_device=device, is_otp_enabled=True)

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

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        user = self.request.user
        device_classes = get_device_classes()

        kwargs_upd = {}
        for device_class in device_classes:
            kwargs_upd[device_class.__name__.lower() + '_set'] = device_class.objects.filter(
                user=user).prefetch_related('device_ptr')

        kwargs.update(kwargs_upd)
        kwargs.update({
            'default_device': default_device(self.request.user, None),
            'device_classes': device_classes
        })
        return kwargs

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
            'issuer': get_current_site(self.request).name  # TODO ...
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    form_class = DeviceUpdateForm
    model = Device
    success_url = reverse_lazy('auth:mfa-detail')
