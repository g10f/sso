import json

from u2flib_server import u2f_v2

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from sso.auth.forms.profile import TOTPDeviceForm, ProfileForm, PhoneSetupForm, AddPhoneForm, AddU2FForm
from sso.auth.models import TwilioSMSDevice, U2FDevice
from sso.auth.utils import class_view_decorator, default_device, random_hex, get_device_classes


@class_view_decorator(login_required)
class AddU2FView(FormView):
    template_name = 'auth/u2f/add_device.html'
    form_class = AddU2FForm
    success_url = reverse_lazy('auth:profile')
    challenge = None

    def get(self, request, *args, **kwargs):
        self.challenge = u2f_v2.start_register(self.get_origin())
        return super(AddU2FView, self).get(request, *args, **kwargs)

    def get_origin(self):
        return '{scheme}://{host}'.format(
            # BBB: Django >= 1.7 has request.scheme
            scheme='https' if self.request.is_secure() else 'http',
            host=self.request.get_host(),
        )

    def get_context_data(self, **kwargs):
        kwargs = super(AddU2FView, self).get_context_data(**kwargs)

        kwargs['challenge'] = json.dumps(self.challenge)

        # Create a SignRequest for each key that has already been added to the
        # account.
        # This can be passed to u2f.register as the second parameter to prevent
        # re-registering the same key for the same user.
        u2f_devices = U2FDevice.objects.filter(user=self.request.user, confirmed=True)
        sign_requests = [
            u2f_v2.start_authenticate(d.to_json()) for d in u2f_devices
        ]
        kwargs['sign_requests'] = json.dumps(sign_requests)

        return kwargs

    def form_valid(self, form):
        response = form.cleaned_data['response']
        challenge = form.cleaned_data['challenge']
        device, attestation_cert = u2f_v2.complete_register(challenge, response)
        U2FDevice.objects.create(user=self.request.user, public_key=device['publicKey'], key_handle=device['keyHandle'],
                                 app_id=device['appId'], confirmed=True)
        # messages.success(self.request, 'U2F device added.')
        return super(AddU2FView, self).form_valid(form)

    def get_initial(self):
        initial = super(AddU2FView, self).get_initial()
        if self.challenge is not None:
            initial.update({'challenge': json.dumps(self.challenge)})
        return initial


@class_view_decorator(login_required)
class ProfileView(FormView):
    """
    View used by users for managing two-factor configuration.

    This view shows whether two-factor has been configured for the user's
    account. If two-factor is enabled, it also lists the primary verification
    method and backup verification methods.
    """
    template_name = 'auth/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('auth:profile')

    def get_context_data(self, **kwargs):
        kwargs = super(ProfileView, self).get_context_data(**kwargs)
        user = self.request.user
        device_classes = get_device_classes()

        kwargs_upd = {}
        for device_class in device_classes:
            kwargs_upd[device_class.__name__.lower() + '_set'] = device_class.objects.filter(user=user).prefetch_related('device_ptr')

        kwargs.update(kwargs_upd)
        kwargs.update({
            'default_device': default_device(self.request.user, None),
            'device_classes': device_classes
        })
        return kwargs

    def get_form_kwargs(self):
        kwargs = super(ProfileView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(ProfileView, self).form_valid(form)


@class_view_decorator(login_required)
class TOTPSetup(FormView):
    template_name = 'auth/totp_setup.html'
    form_class = TOTPDeviceForm
    success_url = reverse_lazy('auth:profile')

    def __init__(self, **kwargs):
        super(TOTPSetup, self).__init__(**kwargs)
        self.initial.update({'key': random_hex(20).decode('ascii')})

    def get_form_kwargs(self):
        kwargs = super(TOTPSetup, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
            'issuer': get_current_site(self.request).name  # TODO ...
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(TOTPSetup, self).form_valid(form)




@class_view_decorator(login_required)
class AddPhoneView(FormView):
    template_name = 'auth/add_phone.html'
    form_class = AddPhoneForm
    success_url = reverse_lazy('auth:phone_setup')

    def __init__(self, **kwargs):
        super(AddPhoneView, self).__init__(**kwargs)
        self.initial.update({'key': random_hex(20).decode('ascii')})

    def get_form_kwargs(self):
        kwargs = super(AddPhoneView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        sms_device = form.save()
        challenge = sms_device.generate_challenge()
        messages.add_message(self.request, level=messages.INFO, message=challenge, fail_silently=True)
        self.success_url = reverse_lazy('auth:phone_setup', kwargs={'sms_device_id': sms_device.pk})
        return super(AddPhoneView, self).form_valid(form)


@class_view_decorator(login_required)
class PhoneSetupView(FormView):
    template_name = 'auth/phone_setup.html'
    form_class = PhoneSetupForm
    success_url = reverse_lazy('auth:profile')

    def post(self, request, *args, **kwargs):
        if request.POST.get('resend_token'):
            sms_device = TwilioSMSDevice.objects.get(user=self.request.user, pk=self.kwargs['sms_device_id'])
            challenge = sms_device.generate_challenge()
            messages.add_message(self.request, level=messages.INFO, message=challenge, fail_silently=True)
            return redirect('auth:phone_setup', sms_device.pk)

        return super(PhoneSetupView, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        sms_device = TwilioSMSDevice.objects.get(user=self.request.user, pk=self.kwargs['sms_device_id'])

        kwargs = super(PhoneSetupView, self).get_form_kwargs()
        kwargs.update({
            'sms_device': sms_device
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(PhoneSetupView, self).form_valid(form)
