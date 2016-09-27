from django.contrib.auth.password_validation import password_validators_help_texts
from django.core.exceptions import ObjectDoesNotExist

from django.db.models import Q
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.shortcuts import render, redirect, resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME, logout as auth_logout
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse
from django.core.mail import mail_managers
from django.utils.html import strip_tags
from django.utils.translation import ugettext as _
from django.forms.models import inlineformset_factory
from sso.oauth2.models import allowed_hosts
from sso.forms.helpers import ErrorList, ChangedDataList, log_change
from sso.organisations.models import is_validation_period_active
from sso.utils.url import get_safe_redirect_uri, update_url
from sso.accounts.tokens import email_confirm_token_generator
from sso.accounts.models import User, UserAddress, UserPhoneNumber, UserEmail, get_applicationrole_ids, Application
from sso.accounts.email import send_useremail_confirmation, send_mail_managers
from sso.accounts.forms import PasswordResetForm, SetPasswordForm, ContactForm, AddressForm, PhoneNumberForm, \
    SelfUserEmailForm, SetPictureAndPasswordForm, PasswordChangeForm
from sso.accounts.forms import UserSelfProfileForm, UserSelfProfileDeleteForm, CenterSelfProfileForm
from sso.auth import update_session_auth_hash

import logging

logger = logging.getLogger(__name__)


LOGIN_FORM_KEY = 'login_form_key'


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            html_message = render_to_string('accounts/email/contact_email.html', cd)
            send_mail_managers(cd['subject'], message=strip_tags(html_message), html_message=html_message, fail_silently=settings.DEBUG)
            return redirect('accounts:contact_thanks')
    else:
        initial = {}
        if request.user.is_authenticated():
            initial['email'] = request.user.primary_email()
            initial['name'] = request.user.get_full_name()
        form = ContactForm(initial=initial)
        
    dictionary = {'form': form}
    return render(request, 'accounts/contact_form.html', dictionary)


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
            # except the current one if
            # django.contrib.auth.middleware.SessionAuthenticationMiddleware
            # is enabled.
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

    return TemplateResponse(request,template_name, context)


def password_change_done(request):
    """
    Displays the "success" page after a password change.
    """
    from django.contrib.auth.views import password_change_done
    defaults = {
        'extra_context': {'redirect_uri': get_safe_redirect_uri(request, allowed_hosts())},
        'template_name': 'accounts/password_change_done.html',
    }
    return password_change_done(request, **defaults)


@never_cache
def logout(request, next_page=None,
           template_name='accounts/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    TODO: replace next with post_logout_redirect_uri
    see http://openid.net/specs/openid-connect-session-1_0.html#RPLogout
    """
    auth_logout(request)
    redirect_to = get_safe_redirect_uri(request, allowed_hosts())
    if redirect_to is None:
        # try deprecated version with parameter name "next"
        redirect_to = get_safe_redirect_uri(request, allowed_hosts(), redirect_field_name=redirect_field_name)
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
        uid = urlsafe_base64_decode(uidb64)
        user_email = UserEmail.objects.get(pk=uid, user=request.user)
    except (TypeError, ValueError, OverflowError, UserEmail.DoesNotExist):
        messages.error(request, _('The confirmation was not succesfull, please resend the confirmation.'))
        user_email = None

    if user_email is not None and user_email.confirmed:
        messages.info(request, _('Your email address \"%(email)s\" was already confirmed successfully.') % {'email': user_email})
    elif user_email is not None and email_confirm_token_generator.check_token(user_email, token):
        user_email.confirmed = True
        user_email.save()
        messages.success(request, _('Your email address \"%(email)s\" was confirmed successfully.') % {'email': user_email})
    elif user_email is not None:
        messages.error(request, _('The confirmation message has probably already expired, please resend the confirmation.'))

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
                messages.success(request, _('The email \"%(email)s\" was deleted successfully.') % {'email': user_email})
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
            form = SelfUserEmailForm(request.POST)
            if form.is_valid():
                user_email = form.save()
                change_message = ChangedDataList(form, []).change_message()
                log_change(request, user, change_message)
                msg = _('Thank you. Your data were saved.') + '\n'
                msg += _('Confirmation email was sent to \"%(email)s\".') % {'email': user_email}
                messages.success(request, msg)
                send_useremail_confirmation(user_email, request)
                return redirect(post_change_redirect)
    else:
        form = SelfUserEmailForm(initial={'user': user.id})

    context = {
        'form': form,
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

    dictionary = {'form': form, 'redirect_uri': redirect_uri}
    return render(request, 'accounts/profile_form_center.html', dictionary)


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

    dictionary = {'form': form, 'redirect_uri': redirect_uri, 'is_validation_period_active': is_validation_period_active(user_organisation)}
    return render(request, 'accounts/profile_core_form.html', dictionary)
    

@login_required
def profile_with_address_and_phone(request, redirect_uri=None):
    address_extra = 0
    phonenumber_extra = 1
    user = request.user
    address_count = user.useraddress_set.count()
    if address_count == 0: 
        address_extra = 1
    
    AddressInlineFormSet = inlineformset_factory(User, UserAddress, AddressForm, extra=address_extra, max_num=3)
    PhoneNumberInlineFormSet = inlineformset_factory(User, UserPhoneNumber, PhoneNumberForm, extra=phonenumber_extra, max_num=6)
    
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

    dictionary = {'form': form, 'errors': errors, 'formsets': formsets, 'media': media, 'active': active,
                  'redirect_uri': redirect_uri, 'is_validation_period_active': is_validation_period_active(user_organisation)}
    return render(request, 'accounts/profile_form.html', dictionary)


@login_required
def delete_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserSelfProfileDeleteForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            auth_logout(request)
            return redirect('home')
    else:
        form = UserSelfProfileDeleteForm(instance=user)
    dictionary = {'form': form, }
    return render(request, 'accounts/delete_profile_form.html', dictionary)


# Doesn't need csrf_protect since no-one can guess the URL
@csrf_exempt
@sensitive_post_parameters()
@never_cache
def password_create_confirm(request, uidb64=None, token=None, template_name='accounts/password_create_confirm.html'):
    """
    View that checks the hash in a password create link and presents a
    form for entering a  password and a picture
    """
    assert uidb64 is not None and token is not None  # checked by URLconf
    post_reset_redirect = reverse('accounts:password_create_complete', args=[uidb64])
    try:
        uid = urlsafe_base64_decode(uidb64)
        user = User._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        title = _('Enter new password')
        if request.method == 'POST':
            form = SetPictureAndPasswordForm(user, request.POST, files=request.FILES)
            if form.is_valid():
                user = form.save()
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = SetPictureAndPasswordForm(user)
    else:
        validlink = False
        form = None
        title = _('Password create unsuccessful')
    context = {
        'form': form,
        'title': title,
        'validlink': validlink,
        'password_validators_help_texts': password_validators_help_texts(),
    }
    return TemplateResponse(request, template_name, context)


def password_create_complete(request, uidb64=None):
    from django.contrib.auth.views import password_reset_complete
    login_url = resolve_url(settings.LOGIN_URL)
    if uidb64 is not None:
        # try to find the first application with redirect_to_after_first_login
        try:
            uid = urlsafe_base64_decode(uidb64)
            applicationrole_ids = get_applicationrole_ids(uid, Q(application__redirect_to_after_first_login=True))
            if applicationrole_ids:
                app = Application.objects.distinct().filter(applicationrole__in=applicationrole_ids, is_active=True).first()
                if app is not None and app.url:
                    login_url = update_url(login_url, {REDIRECT_FIELD_NAME: app.url})
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.exception(e)

    defaults = {
        'extra_context': {'login_url': login_url},
        'template_name': 'accounts/password_create_complete.html',
    }
    return password_reset_complete(request, **defaults)


# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above

@csrf_protect
def password_reset(request, is_admin_site=False):
    from django.contrib.auth.views import password_reset
    defaults = {
        'post_reset_redirect': reverse('accounts:password_reset_done'),
        'template_name': 'accounts/password_reset_form.html',
        'email_template_name': 'accounts/email/password_reset_email.txt',
        'html_email_template_name': 'accounts/email/password_reset_email.html',
        'subject_template_name': 'accounts/email/password_reset_subject.txt',
        'password_reset_form': PasswordResetForm
    }
    return password_reset(request, **defaults)


def password_reset_confirm(request, uidb64=None, token=None):
    from django.contrib.auth.views import password_reset_confirm
    defaults = {
        'set_password_form': SetPasswordForm,
        'post_reset_redirect': reverse('accounts:password_reset_complete'),
        'template_name': 'accounts/password_reset_confirm.html',
        'extra_context': {'password_validators_help_texts': password_validators_help_texts()},
    }
    return password_reset_confirm(request, uidb64, token, **defaults)


def password_reset_done(request):
    from django.contrib.auth.views import password_reset_done
    defaults = {
        'template_name': 'accounts/password_reset_done.html',
    }
    return password_reset_done(request, **defaults)


def password_reset_complete(request):
    from django.contrib.auth.views import password_reset_complete
    defaults = {
        'template_name': 'accounts/password_reset_complete.html',
    }
    return password_reset_complete(request, **defaults)
