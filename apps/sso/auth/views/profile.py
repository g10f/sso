from django.shortcuts import redirect
from django.contrib import messages

from django.core.urlresolvers import reverse_lazy
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.decorators import login_required
from django.views.generic import FormView
from sso.auth.forms.profile import TOTPDeviceForm, ProfileForm, PhoneSetupForm, AddPhoneForm
from sso.auth.models import TOTPDevice, TwilioSMSDevice
from sso.auth.utils import class_view_decorator, default_device, random_hex


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
        totpdevices = TOTPDevice.objects.filter(user=user).prefetch_related('device_ptr')
        twiliosmsdevices = TwilioSMSDevice.objects.filter(user=user).prefetch_related('device_ptr')
        device_classes = [TOTPDevice, TwilioSMSDevice]
        kwargs.update({
            'totpdevice': totpdevices.first(),
            'twiliosmsdevices': twiliosmsdevices,
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
