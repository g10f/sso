import datetime
import logging
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.forms import bootstrap
from sso.forms.fields import Base64ImageField
from ..models import User

logger = logging.getLogger(__name__)


class SetPasswordForm(DjangoSetPasswordForm):
    """
    A form that lets a user change set their password without entering the old
    password.

    When the user has no confirmed emails, then the primary email will be confirmed by save
    """
    new_password1 = forms.CharField(label=_("New password"), widget=bootstrap.PasswordInput())
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=bootstrap.PasswordInput())

    def save(self, commit=True):
        self.user = super().save(commit)
        self.user.confirm_primary_email_if_no_confirmed()

        return self.user


class PasswordChangeForm(DjangoSetPasswordForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    old_password = forms.CharField(label=_("Old password"), widget=bootstrap.PasswordInput())
    new_password1 = forms.CharField(label=_("New password"), widget=bootstrap.PasswordInput())
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=bootstrap.PasswordInput())

    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    })

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'])
        return old_password


PasswordChangeForm.base_fields = OrderedDict(
    (k, PasswordChangeForm.base_fields[k])
    for k in ['old_password', 'new_password1', 'new_password2']
)


class PasswordResetForm(DjangoPasswordResetForm):
    """
    changes from django default PasswordResetForm:
     * validates that the email exists and shows an error message if not.
     * adds an expiration_date to the rendering context
    """
    error_messages = {
        'unknown': _("That email address doesn't have an associated user account. Are you sure you've registered?"),
        'unusable': _("The user account associated with this email address cannot reset the password."),
        'not_activated': _("You can not reset your password jet, because your account is waiting for initial "
                           "activation."),
    }
    email = forms.EmailField(label=_("Email"), max_length=254, widget=bootstrap.EmailInput())

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        try:
            user = User.objects.get_by_confirmed_or_primary_email(email)
            if user.has_usable_password() and user.is_active:
                return email
            # no user with this email and a usable password found
            raise forms.ValidationError(self.error_messages['unusable'])
        except ObjectDoesNotExist:
            raise forms.ValidationError(self.error_messages['unknown'])

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None,
             html_email_template_name='registration/password_reset_email.html',
             extra_email_context=None):
        email = self.cleaned_data["email"]
        current_site = get_current_site(request)
        site_name = settings.SSO_SITE_NAME
        domain = current_site.domain

        user = User.objects.get_by_confirmed_or_primary_email(email)

        # Make sure that no email is sent to a user that actually has
        # a password marked as unusable
        if not user.has_usable_password():
            logger.error("user has unusable password")
        expiration_date = now() + datetime.timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        c = {
            'first_name': user.first_name,
            'email': user.primary_email(),
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'user': user,
            'token': token_generator.make_token(user),
            'protocol': 'https' if use_https else 'http',
            'expiration_date': expiration_date
        }
        subject = loader.render_to_string(subject_template_name, c)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        message = loader.render_to_string(email_template_name, c)
        html_message = None  # loader.render_to_string(html_email_template_name, c)

        user.email_user(subject, message, from_email, html_message=html_message)


class SetPictureAndPasswordForm(SetPasswordForm):
    """
    for new created users with an optional picture field
    """

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        if user and not user.picture:
            self.fields['picture'] = Base64ImageField(label=_('Your picture'), required=settings.SSO_USER_PICTURE_REQUIRED,
                                                      help_text=_('Please use a photo of your face.'),
                                                      widget=bootstrap.ClearableBase64ImageWidget(attrs={
                                                          'max_file_size': settings.SSO_USER_MAX_PICTURE_SIZE,
                                                          'width': settings.SSO_USER_PICTURE_WIDTH,
                                                          'height': settings.SSO_USER_PICTURE_HEIGHT,
                                                      }))

    def save(self, commit=True):
        cd = self.cleaned_data
        if 'picture' in self.changed_data:
            self.user.picture.delete(save=False)
            self.user.picture = cd['picture'] if cd['picture'] else None

        self.user = super().save(commit)
        return self.user
