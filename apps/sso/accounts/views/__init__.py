# -*- coding: utf-8 -*-
from urlparse import urlparse
from django.contrib.auth.tokens import default_token_generator

from django.utils.http import urlsafe_base64_decode, is_safe_url
from django.conf import settings
from django.shortcuts import render, redirect, resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login as auth_login, REDIRECT_FIELD_NAME, logout as auth_logout
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.core.mail import mail_managers
from django.utils.html import strip_tags
from django.utils.translation import ugettext as _
from django.forms.models import inlineformset_factory
from sso.accounts.tokens import email_confirm_token_generator
from throttle.decorators import throttle
from sso.auth.forms import EmailAuthenticationForm
from sso.oauth2.models import get_oauth2_cancel_url
from sso.forms.helpers import ErrorList, ChangedDataList, log_change
from ..models import Application, User, UserAddress, UserPhoneNumber, UserEmail
from ..email import send_useremail_confirmation
from ..forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm, ContactForm, AddressForm, PhoneNumberForm, \
    SelfUserEmailForm, SetPictureAndPasswordForm
from ..forms import UserSelfProfileForm, UserSelfProfileDeleteForm, CenterSelfProfileForm


LOGIN_FORM_KEY = 'login_form_key'


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            html_message = render_to_string('accounts/email/contact_email.html', cd)
            mail_managers(cd['subject'], strip_tags(html_message), html_message=html_message)
            return redirect('accounts:contact_thanks')
    else:
        initial = {}
        if request.user.is_authenticated():
            initial['email'] = request.user.primary_email()
            initial['name'] = request.user.get_full_name()            
        form = ContactForm(initial=initial)
        
    dictionary = {'form': form}
    return render(request, 'accounts/contact_form.html', dictionary)

    
def password_change(request):
    """
    Handles the "change password" task -- both form display and validation.
    """
    from django.contrib.auth.views import password_change
    url = reverse('accounts:password_change_done')
    defaults = {
        'password_change_form': PasswordChangeForm,
        'post_change_redirect': url,
        'template_name': 'accounts/password_change_form.html',
    }
    return password_change(request, **defaults)


def password_change_done(request, extra_context=None):
    """
    Displays the "success" page after a password change.
    """
    from django.contrib.auth.views import password_change_done
    defaults = {
        'extra_context': extra_context or {},
        'template_name': 'accounts/password_change_done.html',
    }
    return password_change_done(request, **defaults)


def get_allowed_hosts():
    allowed_hosts = cache.get('allowed_hosts', [])
    if not allowed_hosts:
        for app in Application.objects.all():
            netloc = urlparse(app.url)[1]
            if netloc:
                allowed_hosts.append(netloc)
        cache.set('allowed_hosts', allowed_hosts)

    return allowed_hosts


def is_safe_ext_url(url, hosts):
    """
    like django.util.http.is_safe_url but with a list of hosts instead one host name

    Return ``True`` if the url is a safe redirection (i.e. it doesn't point to
    a different host and uses a safe scheme).

    Always returns ``False`` on an empty url.
    """
    if not url:
        return False
    url = url.strip()
    # Chrome treats \ completely as /
    url = url.replace('\\', '/')
    # Chrome considers any URL with more than two slashes to be absolute, but
    # urlparse is not so flexible. Treat any url with three slashes as unsafe.
    if url.startswith('///'):
        return False
    url_info = urlparse(url)
    # Forbid URLs like http:///example.com - with a scheme, but without a hostname.
    # In that URL, example.com is not the hostname but, a path component. However,
    # Chrome will still consider example.com to be the hostname, so we must not
    # allow this syntax.
    if not url_info.netloc and url_info.scheme:
        return False
    return ((not url_info.netloc or url_info.netloc in hosts) and
            (not url_info.scheme or url_info.scheme in ['http', 'https']))


def get_safe_redirect_url(request, redirect_to):
    # Ensure the user-originating redirection url is safe.
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        return resolve_url(settings.LOGIN_REDIRECT_URL)
    else:
        return redirect_to


@never_cache
def logout(request, next_page=None,
           template_name='accounts/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    """
    auth_logout(request)
    redirect_to = request.REQUEST.get(redirect_field_name, None)
    if redirect_to and is_safe_ext_url(redirect_to, set(get_allowed_hosts())):
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
        return TemplateResponse(request, template_name, context,
                                current_app=current_app)
    else:
        # Redirect to this page until the session has been cleared.
        return HttpResponseRedirect(next_page or request.path)


@sensitive_post_parameters()
@never_cache
@throttle(duration=30, max_calls=12)
def login(request):
    """
    Displays the login form for the given HttpRequest.
    """
    current_site = get_current_site(request)
    site_name = settings.SSO_SITE_NAME
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    # hidden field in the template to check from which form the post request comes
    login_form_key = request.REQUEST.get(LOGIN_FORM_KEY)  
    display = request.REQUEST.get('display', 'page')  # popup or page
    template_name = 'accounts/login.html'
    cancel_url = get_oauth2_cancel_url(redirect_to)
    form = None

    if request.method == "POST":
        if login_form_key == 'login_form':
            form = EmailAuthenticationForm(data=request.POST)
            if form.is_valid():
                redirect_to = get_safe_redirect_url(request, redirect_to)
    
                # Okay, security checks complete. Log the user in.
                user = form.get_user()
                auth_login(request, user)
    
                if (not user.is_complete) and (display == 'page'):
                    # Display user profile form to complete user data
                    form = UserSelfProfileForm(instance=user)
                    template_name = 'accounts/login_profile_form.html'
                    cancel_url = reverse('accounts:logout')
                else:              
                    return HttpResponseRedirect(redirect_to)
        elif login_form_key == 'login_profile_form':
            user = request.user
            # if the browser back button is used the user may be not authenticated
            if user.is_authenticated():
                form = UserSelfProfileForm(request.POST, instance=user)
                template_name = 'accounts/login_profile_form.html'
                cancel_url = reverse('accounts:logout')
                if form.is_valid():
                    form.save()
                    redirect_to = get_safe_redirect_url(request, redirect_to)
                    return HttpResponseRedirect(redirect_to)

    context = {
        'form': form or EmailAuthenticationForm(request),
        'display': display,
        REDIRECT_FIELD_NAME: redirect_to,
        'cancel_url': cancel_url,
        'site': current_site,
        'site_name': site_name,
        'registration_open': settings.REGISTRATION.get('OPEN', True)
    }
    return TemplateResponse(request, template_name, context)


@login_required
def confirm_email(request, uidb64, token, post_reset_redirect=None):
    if post_reset_redirect is None:
        post_reset_redirect = reverse('accounts:emails')
    else:
        post_reset_redirect = resolve_url(post_reset_redirect)
    try:
        uid = urlsafe_base64_decode(uidb64)
        user_email = UserEmail.objects.get(pk=uid)
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
    user = request.user
    if request.method == 'POST':
        if 'send_confirmation' in request.POST:
            user_email = UserEmail.objects.get(id=request.POST['send_confirmation'])
            send_useremail_confirmation(user_email, request)
            messages.success(request, _('Confirmation email was sent to \"%(email)s\".') % {'email': user_email})
            return redirect('accounts:emails')
        elif 'delete' in request.POST:
            try:
                user_email = UserEmail.objects.get(id=request.POST['delete'])
                user_email.delete()
                messages.success(request, _('The email \"%(email)s\" was deleted successfully.') % {'email': user_email})
            except UserEmail.DoesNotExist:
                # may be a double click on the delete button
                pass
            return redirect('accounts:emails')
        elif 'set_primary' in request.POST:
            user_email = UserEmail.objects.get(id=request.POST['set_primary'])
            user_email.primary = True
            user_email.save()
            UserEmail.objects.filter(user=user_email.user, primary=True).exclude(pk=user_email.pk).update(primary=False)
            messages.success(request, _("The email \"%(email)s\" was changed successfully.") % {'email': user_email})
            return redirect('accounts:emails')
        else:
            form = SelfUserEmailForm(request.POST)
            if form.is_valid():
                user_email = form.save()
                change_message = ChangedDataList(form, []).change_message()
                log_change(request, user, change_message)
                msg = _('Thank you. Your settings were saved.') + '\n'
                msg += _('Confirmation email was sent to \"%(email)s\".') % {'email': user_email}
                messages.success(request, msg)
                send_useremail_confirmation(user_email, request)
                return redirect('accounts:emails')
    else:
        form = SelfUserEmailForm(initial={'user': user.id})

    dictionary = {'form': form, 'max_email_adresses': UserEmail.MAX_EMAIL_ADRESSES}
    return render(request, 'accounts/user_email_detail.html', dictionary)


@login_required
def profile(request):
    if getattr(request.user, 'is_center', False):
        return profile_center_account(request)        
    if settings.SSO_SHOW_ADDRESS_AND_PHONE_FORM:
        return profile_with_address_and_phone(request)
    else:
        return profile_core(request)


@login_required
def profile_center_account(request):
    user = request.user
    if request.method == 'POST':
        form = CenterSelfProfileForm(request.POST, instance=user, files=request.FILES)
        if form.is_valid():
            form.save()
            change_message = ChangedDataList(form, []).change_message() 
            log_change(request, user, change_message)            
            messages.success(request, _('Thank you. Your settings were saved.'))
            return redirect('accounts:profile')
    else:
        form = CenterSelfProfileForm(instance=user)

    dictionary = {'form': form}
    return render(request, 'accounts/profile_form_center.html', dictionary)


@login_required
def profile_core(request):
    user = request.user
    if request.method == 'POST':
        form = UserSelfProfileForm(request.POST, instance=user, files=request.FILES)
        if form.is_valid():
            form.save()
            change_message = ChangedDataList(form, []).change_message() 
            log_change(request, user, change_message)            
            messages.success(request, _('Thank you. Your settings were saved.'))
            return redirect('accounts:profile')
    else:
        form = UserSelfProfileForm(instance=user)

    dictionary = {'form': form}
    return render(request, 'accounts/profile_core_form.html', dictionary)
    

@login_required
def profile_with_address_and_phone(request):
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
            
            messages.success(request, _('Thank you. Your settings were saved.'))

            return redirect('accounts:profile')
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

    dictionary = {'form': form, 'errors': errors, 'formsets': formsets, 'media': media, 'active': active}
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
@sensitive_post_parameters()
@never_cache
def password_create_confirm(request, uidb64=None, token=None, template_name='accounts/password_create_confirm.html'):
    """
    View that checks the hash in a password create link and presents a
    form for entering a  password and a picture
    """
    assert uidb64 is not None and token is not None  # checked by URLconf
    post_reset_redirect = reverse('accounts:password_create_complete')
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
    }
    return TemplateResponse(request, template_name, context)


def password_create_complete(request):
    from django.contrib.auth.views import password_reset_complete
    defaults = {
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
        'email_template_name': 'accounts/email/password_reset_email.html',
        'subject_template_name': 'accounts/email/password_reset_subject.txt',
        'password_reset_form': PasswordResetForm
    }
    return password_reset(request, is_admin_site=False, **defaults)


def password_reset_confirm(request, uidb64=None, token=None):
    from django.contrib.auth.views import password_reset_confirm
    defaults = {
        'set_password_form': SetPasswordForm,
        'post_reset_redirect': reverse('accounts:password_reset_complete'),
        'template_name': 'accounts/password_reset_confirm.html',
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
