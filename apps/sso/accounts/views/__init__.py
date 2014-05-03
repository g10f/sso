# -*- coding: utf-8 -*-
import urlparse
import urllib
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, REDIRECT_FIELD_NAME, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, QueryDict
from django.template.response import TemplateResponse
from django.template.loader import render_to_string
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.core.mail import mail_managers
from django.utils.html import strip_tags
from django.db.models import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from django.forms.models import inlineformset_factory

from throttle.decorators import throttle
from sso.auth.forms import EmailAuthenticationForm
from sso.oauth2.models import get_oauth2_cancel_url
from sso.forms.helpers import ErrorList, ChangedDataList, log_change 

from ..models import Application, User, UserAddress, UserPhoneNumber
from ..forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm, ContactForm, AddressForm, PhoneNumberForm
from ..forms import UserSelfProfileForm, UserSelfProfileDeleteForm

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
            initial['email'] = request.user.email
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
            netloc = urlparse.urlparse(app.url)[1]
            if netloc:
                allowed_hosts.append(netloc)
        cache.set('allowed_hosts', allowed_hosts)

    return allowed_hosts


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
    if redirect_to:
        netloc = urlparse.urlparse(redirect_to)[1]
        # Security check -- don't allow redirection to a different host.
        allowed_hosts = get_allowed_hosts()
        if not(netloc and not (netloc in set([request.get_host()]) | set(allowed_hosts))):
            return HttpResponseRedirect(redirect_to)

    if next_page is None:
        current_site = get_current_site(request)
        site_name = settings.SSO_CUSTOM['SITE_NAME']
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


def _check_redirect_url(request, redirect_to):
    """
    helper to make login more DRY
    """
    netloc = urlparse.urlparse(redirect_to)[1]
    # Use default setting if redirect_to is empty
    if not redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL

    # Heavier security check -- don't allow redirection to a different
    # host.
    elif netloc and netloc != request.get_host():
        redirect_to = settings.LOGIN_REDIRECT_URL
    
    return redirect_to
    
    
@sensitive_post_parameters()
@never_cache
@throttle(duration=30, max_calls=12)
def login(request):
    """
    Displays the login form for the given HttpRequest.
    """
    current_site = get_current_site(request)
    site_name = settings.SSO_CUSTOM['SITE_NAME']
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
                redirect_to = _check_redirect_url(request, redirect_to)
    
                # Okay, security checks complete. Log the user in.
                user = form.get_user()
                auth_login(request, user)
    
                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()
    
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
                        
                    redirect_to = _check_redirect_url(request, redirect_to)
                    return HttpResponseRedirect(redirect_to)

    request.session.set_test_cookie()

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
def profile(request):
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


@csrf_protect
def password_reset(request, is_admin_site=False,
                   template_name='accounts/password_reset_form.html',
                   email_template_name='accounts/password_reset_email.html',
                   subject_template_name='registration/password_reset_subject.txt',
                   password_reset_form=PasswordResetForm):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            opts = {
                'use_https': request.is_secure(),
                'email_template_name': email_template_name,
                'subject_template_name': subject_template_name,
                'request': request,
            }
            if is_admin_site:
                opts = dict(opts, domain_override=request.get_host())
            form.save(**opts)
            
            if (not form.password):            
                post_reset_redirect = reverse('accounts:password_reset_done')
            else:
                # special case for streaming accounts, where there is no account in the sso database.
                # these accounts get the password directly send
                post_reset_redirect = reverse('accounts:password_resend_done')
                
            return HttpResponseRedirect(post_reset_redirect)
    else:
        form = password_reset_form()
    context = {
        'form': form,
    }
    return TemplateResponse(request, template_name, context)


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
