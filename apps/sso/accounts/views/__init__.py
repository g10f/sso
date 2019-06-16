import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import password_validators_help_texts
from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, resolve_url
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from sso.accounts.email import send_useremail_confirmation, send_mail_managers
from sso.accounts.forms import PasswordResetForm, SetPasswordForm, ContactForm, AddressForm, PhoneNumberForm, \
    SetPictureAndPasswordForm, PasswordChangeForm, SelfUserEmailAddForm
from sso.accounts.forms import UserSelfProfileForm, UserSelfProfileDeleteForm, CenterSelfProfileForm
from sso.accounts.models import User, UserAddress, UserPhoneNumber, UserEmail, get_applicationrole_ids, Application
from sso.accounts.tokens import email_confirm_token_generator
from sso.auth import update_session_auth_hash, auth_login, is_otp_login
from sso.auth.views import get_token_url
from sso.forms.helpers import ErrorList, ChangedDataList, log_change
from sso.oauth2.models import allowed_hosts
from sso.organisations.models import is_validation_period_active
from sso.utils.url import get_safe_redirect_uri, update_url, REDIRECT_URI_FIELD_NAME

logger = logging.getLogger(__name__)

LOGIN_FORM_KEY = 'login_form_key'
OIDC_LOGOUT_REDIRECT_FIELD_NAME = 'post_logout_redirect_uri'


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            html_message = render_to_string('accounts/email/contact_email.html', cd)
            send_mail_managers(cd['subject'], message=strip_tags(html_message), html_message=html_message,
                               fail_silently=settings.DEBUG, reply_to=[cd['email']])
            return redirect('accounts:contact_thanks')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['email'] = request.user.primary_email()
            initial['name'] = request.user.get_full_name()
        form = ContactForm(initial=initial)

    context = {'form': form}
    return render(request, 'accounts/contact_form.html', context)


@sensitive_post_parameters()
@csrf_protect
@login_required
def password_change(request):
    """
    Handles the "change password" task -- both form display and validation.
    """
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    post_change_redirect = update_url(reverse('accounts:password_change_done'), {'redirect_uri': redirect_uri})
    template_name = 'accounts/password_change_form.html'
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Updating the password logs out all other sessions for the user
            # except the current one
            update_session_auth_hash(request, form.user)
            return HttpResponseRedirect(post_change_redirect)
    else:
        form = PasswordChangeForm(user=request.user)
    context = {
        'password_validators_help_texts': password_validators_help_texts(),
        'form': form,
        'title': _('Password change'),
        'redirect_uri': redirect_uri
    }

    return TemplateResponse(request, template_name, context)


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['redirect_uri'] = get_safe_redirect_uri(self.request, allowed_hosts())
        return context


@never_cache
def logout(request, next_page=None,
           template_name='accounts/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    see http://openid.net/specs/openid-connect-session-1_0.html#RPLogout
    """
    auth_logout(request)
    redirect_uris = [redirect_field_name, REDIRECT_URI_FIELD_NAME, OIDC_LOGOUT_REDIRECT_FIELD_NAME]
    redirect_to = get_safe_redirect_uri(request, allowed_hosts(), redirect_uris)
    if redirect_to:
        return HttpResponseRedirect(redirect_to)

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


@login_required
def confirm_email(request, uidb64, token, post_reset_redirect=None):
    if post_reset_redirect is None:
        post_reset_redirect = reverse('accounts:emails')
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user_email = UserEmail.objects.get(pk=uid, user=request.user)
    except (TypeError, ValueError, OverflowError, UserEmail.DoesNotExist):
        messages.error(request, _('The confirmation was not succesfull, please resend the confirmation.'))
        user_email = None

    if user_email is not None and user_email.confirmed:
        messages.info(request,
                      _('Your email address \"%(email)s\" was already confirmed successfully.') % {'email': user_email})
    elif user_email is not None and email_confirm_token_generator.check_token(user_email, token):
        user_email.confirmed = True
        user_email.save()
        messages.success(request,
                         _('Your email address \"%(email)s\" was confirmed successfully.') % {'email': user_email})
    elif user_email is not None:
        messages.error(request,
                       _('The confirmation message has probably already expired, please resend the confirmation.'))

    return HttpResponseRedirect(post_reset_redirect)


@login_required
@user_passes_test(lambda user: not user.is_center)
def emails(request):
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    post_change_redirect = update_url(reverse('accounts:emails'), {'redirect_uri': redirect_uri})

    user = request.user
    if request.method == 'POST':
        if 'send_confirmation' in request.POST:
            user_email = UserEmail.objects.get(id=request.POST['send_confirmation'])
            send_useremail_confirmation(user_email, request)
            messages.success(request, _('Confirmation email was sent to \"%(email)s\".') % {'email': user_email})
            return redirect(post_change_redirect)
        elif 'delete' in request.POST:
            try:
                user_email = UserEmail.objects.get(id=request.POST['delete'])
                user_email.delete()
                messages.success(request,
                                 _('The email \"%(email)s\" was deleted successfully.') % {'email': user_email})
            except UserEmail.DoesNotExist:
                # may be a double click on the delete button
                pass
            return redirect(post_change_redirect)
        elif 'set_primary' in request.POST:
            user_email = UserEmail.objects.get(id=request.POST['set_primary'])
            user_email.primary = True
            user_email.save()
            UserEmail.objects.filter(user=user_email.user, primary=True).exclude(pk=user_email.pk).update(primary=False)
            messages.success(request, _("The email \"%(email)s\" was changed successfully.") % {'email': user_email})
            return redirect(post_change_redirect)
        else:
            add_form = SelfUserEmailAddForm(request.POST)
            if add_form.is_valid():
                user_email = add_form.save()
                change_message = ChangedDataList(add_form, []).change_message()
                log_change(request, user, change_message)
                msg = _('Thank you. Your data were saved.') + '\n'
                msg += _('Confirmation email was sent to \"%(email)s\".') % {'email': user_email}
                messages.success(request, msg)
                send_useremail_confirmation(user_email, request)
                return redirect(post_change_redirect)
    else:
        add_form = SelfUserEmailAddForm(initial={'user': user.id})

    context = {
        'form': add_form,
        'max_email_adresses': UserEmail.MAX_EMAIL_ADRESSES,
        'redirect_uri': redirect_uri
    }
    return render(request, 'accounts/user_email_detail.html', context)


def get_profile_success_url(request, redirect_uri):
    if "_continue" in request.POST:
        if redirect_uri:
            success_url = update_url(reverse('accounts:profile'), {'redirect_uri': redirect_uri})
        else:
            success_url = reverse('accounts:profile')
        messages.success(request, _('Your profile was changed successfully. You may edit it again below.'))
    else:
        if redirect_uri:
            success_url = redirect_uri
        else:
            success_url = reverse('home')
            messages.success(request, _('Thank you. Your profile was saved.'))

    return success_url


@login_required
def profile(request):
    redirect_uri = get_safe_redirect_uri(request, allowed_hosts())
    if getattr(request.user, 'is_center', False):
        return profile_center_account(request, redirect_uri)
    if settings.SSO_SHOW_ADDRESS_AND_PHONE_FORM:
        return profile_with_address_and_phone(request, redirect_uri)
    else:
        return profile_core(request, redirect_uri)


@login_required
def profile_center_account(request, redirect_uri=None):
    user = request.user
    if request.method == 'POST':
        form = CenterSelfProfileForm(request.POST, instance=user, files=request.FILES)
        if form.is_valid():
            form.save()
            change_message = ChangedDataList(form, []).change_message()
            log_change(request, user, change_message)

            success_url = get_profile_success_url(request, redirect_uri)
            return HttpResponseRedirect(success_url)
    else:
        form = CenterSelfProfileForm(instance=user)

    context = {'form': form, 'redirect_uri': redirect_uri}
    return render(request, 'accounts/profile_form_center.html', context)


@login_required
def profile_core(request, redirect_uri=None):
    user = request.user
    if request.method == 'POST':
        form = UserSelfProfileForm(request.POST, instance=user, files=request.FILES)
        if form.is_valid():
            form.save()
            change_message = ChangedDataList(form, []).change_message()
            log_change(request, user, change_message)

            success_url = get_profile_success_url(request, redirect_uri)
            return HttpResponseRedirect(success_url)
    else:
        form = UserSelfProfileForm(instance=user)

    try:
        user_organisation = user.organisations.first()
    except ObjectDoesNotExist:
        user_organisation = None

    context = {'form': form, 'redirect_uri': redirect_uri,
               'is_validation_period_active': is_validation_period_active(user_organisation)}
    return render(request, 'accounts/profile_core_form.html', context)


@login_required
def profile_with_address_and_phone(request, redirect_uri=None):
    address_extra = 0
    phonenumber_extra = 1
    user = request.user
    address_count = user.useraddress_set.count()
    if address_count == 0:
        address_extra = 1

    AddressInlineFormSet = inlineformset_factory(User, UserAddress, AddressForm, extra=address_extra, max_num=3)
    PhoneNumberInlineFormSet = inlineformset_factory(User, UserPhoneNumber, PhoneNumberForm, extra=phonenumber_extra,
                                                     max_num=6)

    if request.method == 'POST':
        form = UserSelfProfileForm(request.POST, instance=user, files=request.FILES)

        address_inline_formset = AddressInlineFormSet(request.POST, instance=user)
        phonenumber_inline_formset = PhoneNumberInlineFormSet(request.POST, instance=user)

        if form.is_valid() and address_inline_formset.is_valid() and phonenumber_inline_formset.is_valid():
            form.save()
            address_inline_formset.save()
            phonenumber_inline_formset.save()

            UserAddress.ensure_single_primary(user)
            UserPhoneNumber.ensure_single_primary(user)

            formsets = [address_inline_formset, phonenumber_inline_formset]
            change_message = ChangedDataList(form, formsets).change_message()
            log_change(request, user, change_message)

            success_url = get_profile_success_url(request, redirect_uri)
            return HttpResponseRedirect(success_url)
    else:
        address_inline_formset = AddressInlineFormSet(instance=user)
        phonenumber_inline_formset = PhoneNumberInlineFormSet(instance=user)
        form = UserSelfProfileForm(instance=user)

    phonenumber_inline_formset.forms += [phonenumber_inline_formset.empty_form]
    address_inline_formset.forms += [address_inline_formset.empty_form]

    formsets = [address_inline_formset, phonenumber_inline_formset]

    media = form.media
    for fs in formsets:
        media = media + fs.media

    errors = ErrorList(form, formsets)
    active = ''
    if errors:
        if not form.is_valid():
            active = 'object'
        else:  # set the first formset with an error as active
            for formset in formsets:
                if not formset.is_valid():
                    active = formset.prefix
                    break

    try:
        user_organisation = user.organisations.first()
    except ObjectDoesNotExist:
        user_organisation = None

    context = {'form': form, 'errors': errors, 'formsets': formsets, 'media': media, 'active': active,
               'redirect_uri': redirect_uri,
               'is_validation_period_active': is_validation_period_active(user_organisation)}
    return render(request, 'accounts/profile_form.html', context)


@login_required
def delete_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserSelfProfileDeleteForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            change_message = ChangedDataList(form, None).change_message()
            log_change(request, user, change_message)
            return redirect('accounts:logout')
    else:
        form = UserSelfProfileDeleteForm(instance=user)
    context = {'form': form, }
    return render(request, 'accounts/delete_profile_form.html', context)


def get_start_app(uidb64):
    # try to find the first application with redirect_to_after_first_login
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        applicationrole_ids = get_applicationrole_ids(uid, Q(application__redirect_to_after_first_login=True))
        if applicationrole_ids:
            app = Application.objects.distinct().filter(applicationrole__in=applicationrole_ids, is_active=True).first()
            if app is not None and app.url:
                return app
    except (TypeError, ValueError, OverflowError) as e:
        logger.exception(e)
    return None


class PasswordCreateConfirmView(auth_views.PasswordResetConfirmView):
    form_class = SetPictureAndPasswordForm
    post_reset_login_backend = settings.DEFAULT_AUTHENTICATION_BACKEND
    template_name = 'accounts/password_create_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_validators_help_texts'] = password_validators_help_texts()
        return context

    def form_valid(self, form):
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
        if settings.SSO_POST_RESET_LOGIN:
            # user has no two factor authentication, because the password was just created
            auth_login(self.request, user, self.post_reset_login_backend)
        return super(auth_views.PasswordResetConfirmView, self).form_valid(form)

    def get_success_url(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        return reverse('accounts:password_create_complete', args=[uidb64])


class PasswordCreateCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'accounts/password_create_complete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uidb64 = kwargs.get('uidb64')
        if uidb64 is not None:
            app = get_start_app(uidb64)
            if app:
                login_url = resolve_url(settings.LOGIN_URL)
                context['login_url'] = update_url(login_url, {REDIRECT_FIELD_NAME: app.url})
                context['app'] = app
        return context


class PasswordResetView(auth_views.PasswordResetView):
    email_template_name = 'accounts/email/password_reset_email.txt'
    form_class = PasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')
    template_name = 'accounts/password_reset_form.html'
    html_email_template_name = 'accounts/email/password_reset_email.html'
    subject_template_name = 'accounts/email/password_reset_subject.txt'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = SetPasswordForm
    post_reset_login_backend = settings.DEFAULT_AUTHENTICATION_BACKEND
    success_url = reverse_lazy('accounts:password_reset_complete')
    template_name = 'accounts/password_reset_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['password_validators_help_texts'] = password_validators_help_texts()
        return context

    def form_valid(self, form):
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
        if settings.SSO_POST_RESET_LOGIN:
            # check if user has 2 factor authentication enabled
            device = is_otp_login(user, is_two_factor_required=False)
            if device:
                redirect_url = reverse('accounts:password_reset_complete')
                self.success_url = get_token_url(user.id, expiry=0, redirect_url=redirect_url,
                                                 backend=self.post_reset_login_backend,
                                                 display=None, device_id=device.id)
            else:
                auth_login(self.request, user, self.post_reset_login_backend)
        return super(auth_views.PasswordResetConfirmView, self).form_valid(form)
