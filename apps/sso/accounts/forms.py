import datetime
import logging
from collections import OrderedDict

import pytz
from captcha.fields import ReCaptchaField

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.template import loader
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_encode
from django.utils.text import capfirst
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from sso.forms import bootstrap, mixins, BLANK_CHOICE_DASH, BaseForm, BaseTabularInlineForm, BaseStackedInlineForm
from sso.forms.fields import EmailFieldLower
from sso.models import clean_picture
from sso.organisations.models import Organisation, is_validation_period_active
from sso.registration import default_username_generator
from sso.registration.forms import UserSelfRegistrationForm
from .models import User, UserAddress, UserPhoneNumber, UserEmail, OrganisationChange, RoleProfile, ApplicationRole
from ..signals import extend_user_validity

logger = logging.getLogger(__name__)


class OrganisationChangeForm(BaseForm):
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.filter(
        is_active=True, is_selectable=True, association__is_selectable=True).only(
        'id', 'location', 'name', 'organisation_country__country__iso2_code', 'association__name').prefetch_related(
        'organisation_country__country', 'association'), label=_("Organisation"), widget=bootstrap.Select2())

    class Meta:
        model = OrganisationChange
        fields = ('organisation', 'message')
        widgets = {
            'message': bootstrap.Textarea()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            # to change the organisation, we need a new "organisation change" because the admin got already an email
            self.fields['organisation'].disabled = True

    def clean_organisation(self):
        organisation = self.cleaned_data['organisation']
        if organisation and organisation in self.initial['user'].organisations.all():
            raise forms.ValidationError(_("The new organisation is the same as the old organisation!"))

        return organisation


class OrganisationChangeAcceptForm(forms.Form):
    """
    Form for organisation admins to accept an request for changing
    the organisation from an user of another organisation
    """

    def __init__(self, organisationchange, *args, **kwargs):
        self.organisationchange = organisationchange
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.organisationchange.is_open:
            raise forms.ValidationError(_('Organisation change was already processed'), code='not-open')

        return super().clean()


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=100, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_("Email address"), max_length=75, widget=bootstrap.TextInput())
    subject = forms.CharField(label=_("Subject"), widget=bootstrap.TextInput())
    message = forms.CharField(label=_("Message"), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    captcha = ReCaptchaField()


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
            self.fields['picture'] = forms.ImageField(label=_('Profile picture'), widget=bootstrap.ImageWidget())

    def clean_picture(self):
        picture = self.cleaned_data["picture"]
        return clean_picture(picture, User.MAX_PICTURE_SIZE)

    def save(self, commit=True):
        cd = self.cleaned_data
        if 'picture' in self.changed_data:
            self.user.picture.delete(save=False)
            self.user.picture = cd['picture'] if cd['picture'] else None

        self.user = super().save(commit)
        return self.user


class AdminUserCreationForm(forms.ModelForm):
    """
    Django Admin Site UserCreationForm where no password is required and the username is created from first_name and
    last_name. If the password is empty, an random password is created
    """
    password1 = forms.CharField(label=_("Password"), required=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), required=False, widget=forms.PasswordInput,
                                help_text=_("Enter the same password as above, for verification."))
    first_name = forms.CharField(label=_('First name'), required=True)
    last_name = forms.CharField(label=_('Last name'), required=True)

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError(self.error_messages['password_mismatch'])

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1", "")
        if password == "":
            password = get_random_string(40)
        user.set_password(password)

        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')),
                                                   capfirst(self.cleaned_data.get('last_name')))

        if commit:
            user.save()
        return user


class UserAddForm(mixins.UserRolesMixin, mixins.UserNoteMixin, forms.ModelForm):
    """
    form for SSO User Admins for adding users in the frontend
    """
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    first_name = forms.CharField(label=_('First name'), required=True,
                                 widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('Last name'), required=True,
                                widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    gender = forms.ChoiceField(label=_('Gender'), required=True, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES),
                               widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False,
                          widget=bootstrap.SelectDateWidget(
                              years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024,
                            widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    organisations = forms.ModelChoiceField(queryset=None, required=settings.SSO_ORGANISATION_REQUIRED,
                                           label=_("Organisation"), widget=bootstrap.Select2())
    application_roles = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Application roles")),
        label=_("Additional application roles"),
        help_text=mixins.UserRolesMixin.application_roles_help)

    role_profiles = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=bootstrap.CheckboxSelectMultiple(),
        label=_("Role profiles"),
        help_text=mixins.UserRolesMixin.role_profiles_help)

    error_messages = {
        'duplicate_email': _("A user with that email address already exists."),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name", 'gender', 'dob', 'notes', 'application_roles', 'role_profiles')

    def __init__(self, request, *args, **kwargs):
        self.request = request
        user = request.user
        super().__init__(*args, **kwargs)
        self.fields['application_roles'].queryset = user.get_administrable_application_roles()
        self.fields['role_profiles'].queryset = user.get_administrable_role_profiles()
        self.fields['organisations'].queryset = user.get_administrable_user_organisations(). \
            filter(is_active=True, association__is_selectable=True)
        if not user.has_perm("accounts.access_all_users"):
            self.fields['organisations'].required = True

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            User.objects.get_by_email(email)
            raise forms.ValidationError(self.error_messages['duplicate_email'])
        except ObjectDoesNotExist:
            pass

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(get_random_string(40))
        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')),
                                                   capfirst(self.cleaned_data.get('last_name')))

        organisation = self.cleaned_data["organisations"]
        if is_validation_period_active(organisation):
            user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        user.save()

        # use mixin to send notification
        self.user = user
        current_user = self.request.user
        self.update_user_m2m_fields('organisations', current_user)
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)

        self.create_note_if_required(current_user, self.cleaned_data)
        user.create_primary_email(email=self.cleaned_data["email"])
        return user


class AddressForm(BaseStackedInlineForm):
    class Meta:
        model = UserAddress
        fields = (
            'primary', 'address_type', 'addressee', 'street_address', 'city', 'city_native', 'postal_code', 'country',
            'region')
        widgets = {
            'primary': bootstrap.CheckboxInput(),
            'address_type': bootstrap.Select(),
            'addressee': bootstrap.TextInput(attrs={'size': 50}),
            'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
            'city': bootstrap.TextInput(attrs={'size': 50}),
            'city_native': bootstrap.TextInput(attrs={'size': 50}),
            'postal_code': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select2(),
            'region': bootstrap.TextInput(attrs={'size': 50}),
        }


class PhoneNumberForm(BaseTabularInlineForm):
    class Meta:
        model = UserPhoneNumber
        fields = ('phone_type', 'phone', 'primary')
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
            'primary': bootstrap.CheckboxInput()
        }


class SelfUserEmailAddForm(forms.Form):
    email = EmailFieldLower(max_length=254, label=_('Email address'), required=False)
    user = forms.IntegerField(widget=forms.HiddenInput())

    error_messages = {
        'duplicate_email': _("The email address \"%(email)s\" is already in use."),
    }

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        if not email:
            raise forms.ValidationError(_('This field is required.'))

        qs = UserEmail.objects.filter(email=email)
        if qs.exists():
            raise forms.ValidationError(self.error_messages['duplicate_email'] % {'email': email})

        return email

    def save(self):
        cd = self.cleaned_data
        user_email = UserEmail(email=cd['email'], user_id=cd['user'])
        user_email.save()
        return user_email


class UserEmailForm(BaseTabularInlineForm):
    class Meta:
        model = UserEmail
        fields = ('email', 'primary', 'confirmed')
        widgets = {
            'email': bootstrap.EmailInput(),
            'primary': bootstrap.CheckboxInput(),
            'confirmed': bootstrap.CheckboxInput()
        }


class UserSelfProfileForm(forms.Form):
    """
    Form for the user himself to change editable values
    """
    username = bootstrap.ReadOnlyField(label=_("Username"))
    valid_until = bootstrap.ReadOnlyField(label=_("Valid until"))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    picture = forms.ImageField(label=_('Picture'), required=False, widget=bootstrap.ImageWidget())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES),
                               widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False,
                          widget=bootstrap.SelectDateWidget(
                              years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)))
    homepage = forms.URLField(label=_('Homepage'), required=False, max_length=512, widget=bootstrap.TextInput())
    language = forms.ChoiceField(label=_("Language"), required=False,
                                 choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])),
                                 widget=bootstrap.Select2())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False,
                                 choices=BLANK_CHOICE_DASH + list(zip(pytz.common_timezones, pytz.common_timezones)),
                                 widget=bootstrap.Select2())

    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        initial = kwargs.get('initial', {})
        object_data.update(initial)
        kwargs['initial'] = object_data
        super().__init__(*args, **kwargs)

        organisation_field = bootstrap.ReadOnlyField(
            initial=', '.join([str(x) for x in self.user.organisations.all()]),
            label=_("Organisation"), help_text=_('Please use the contact form for a request to change this value.'))
        self.fields['organisation'] = organisation_field

    def clean_organisation(self):
        if self.user.organisations.exists():
            # if already assigned to an organisation return None, (readonly use case)
            return None
        else:
            return self.cleaned_data['organisation']

    def clean_picture(self):
        picture = self.cleaned_data["picture"]
        return clean_picture(picture, User.MAX_PICTURE_SIZE)

    def save(self):
        cd = self.cleaned_data
        if (not self.initial['first_name'] and not self.initial['last_name']) and cd.get('first_name') \
                and cd.get('last_name'):
            # should be a streaming user, which has no initial first_name and last_name
            # we create the new username because the streaming user has his email as username
            self.user.username = default_username_generator(capfirst(cd.get('first_name')),
                                                            capfirst(cd.get('last_name')))

        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']

        if 'picture' in self.changed_data:
            self.user.picture.delete(save=False)
        self.user.picture = cd['picture'] if cd['picture'] else None

        self.user.dob = cd.get('dob', None)
        self.user.gender = cd['gender']
        self.user.homepage = cd['homepage']
        self.user.language = cd['language']
        self.user.timezone = cd['timezone']

        self.user.save()

        if 'organisation' in cd and cd['organisation']:
            # user selected an organisation, this can only happen if the user before had
            # no organisation (see clean_organisation).
            self.user.set_organisations([cd["organisation"]])


class CenterSelfProfileForm(forms.Form):
    """
    Form for a user which represents a center
    """
    account_type = bootstrap.ReadOnlyField(label=_("Account type"))
    username = bootstrap.ReadOnlyField(label=_("Username"))
    email = bootstrap.ReadOnlyField(label=_('Email address'))
    language = forms.ChoiceField(label=_("Language"), required=False,
                                 choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])),
                                 widget=bootstrap.Select2())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False,
                                 choices=BLANK_CHOICE_DASH + list(zip(pytz.common_timezones, pytz.common_timezones)),
                                 widget=bootstrap.Select2())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        object_data['account_type'] = _('Organisation Account') if self.user.is_center else _('Member Account')
        object_data['email'] = force_str(self.user.primary_email())
        initial = kwargs.get('initial', {})
        object_data.update(initial)
        kwargs['initial'] = object_data
        super().__init__(*args, **kwargs)

        if self.user.organisations.exists():
            organisation = ', '.join([str(x) for x in self.user.organisations.all()])
            organisation_field = bootstrap.ReadOnlyField(initial=organisation, label=_("Organisation"))
            self.fields['organisation'] = organisation_field

    def save(self):
        cd = self.cleaned_data
        self.user.language = cd['language']
        self.user.timezone = cd['timezone']
        self.user.save()


class UserSelfProfileDeleteForm(mixins.UserNoteMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def save(self):
        self.user.is_active = False
        self.user.save()
        self.create_note_if_required(self.user, activate=False)

    @cached_property
    def changed_data(self):
        return ['is_active']


class UserSelfRegistrationForm2(UserSelfRegistrationForm):
    """
    Overwritten UserSelfRegistrationForm Form with additional organisation field
    """
    organisation = forms.ModelChoiceField(
        queryset=Organisation.objects.filter(is_active=True, is_selectable=True, association__is_selectable=True
                                             ).select_related('organisation_country__country'),
        required=settings.SSO_ORGANISATION_REQUIRED,
        label=_("Organisation"), widget=bootstrap.Select2())
    state = forms.CharField(label=_('State'), required=False, widget=bootstrap.HiddenInput())
    signer = signing.TimestampSigner()

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if self.is_captcha_needed():
            self.fields['captcha'] = ReCaptchaField()

    def is_captcha_needed(self):
        max_age = 100
        if self.data and ('state' in self.data):
            try:
                value = self.signer.unsign(self.data['state'], max_age)
                if value == 'True':
                    return False
            except (signing.BadSignature, signing.SignatureExpired):
                pass
        return True

    def clean(self):
        """
        Delete the captcha field if already one time solved
        """
        if 'captcha' in self.cleaned_data:
            data = self.data.copy()
            data['state'] = self.signer.sign('True')
            self.data = data
            del self.fields['captcha']
        return super().clean()

    @staticmethod
    def save_data(data, username_generator=default_username_generator):
        registration_profile = UserSelfRegistrationForm.save_data(data, username_generator)
        new_user = registration_profile.user

        organisation = data["organisation"]
        if organisation:
            new_user.set_organisations([organisation])

        role_id = None if organisation else settings.SSO_DEFAULT_GUEST_PROFILE_UUID
        default_role_profile = User.get_default_role_profile(role_id)
        if default_role_profile:
            new_user.role_profiles.add(default_role_profile)

        return registration_profile


class UserProfileForm(mixins.UserRolesMixin, mixins.UserNoteMixin, forms.Form):
    """
    Form for SSO Staff
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    username = forms.CharField(label=_("Username"), max_length=40, validators=[UnicodeUsernameValidator()], widget=bootstrap.TextInput())
    valid_until = bootstrap.ReadOnlyField(label=_("Valid until"))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateField(
        label=_('Date of birth'),
        required=False,
        widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)))
    status = bootstrap.ReadOnlyField(label=_('Status'))
    organisations = forms.ModelChoiceField(queryset=None, required=settings.SSO_ORGANISATION_REQUIRED, label=_("Organisation"), widget=bootstrap.Select2())
    application_roles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Application roles")),
        label=_("Additional application roles"),
        help_text=mixins.UserRolesMixin.application_roles_help)
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    role_profiles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.CheckboxSelectMultiple(),
        label=_("Role profiles"),
        help_text=mixins.UserRolesMixin.role_profiles_help)
    created_by_user = forms.CharField(label=_("Created by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    last_modified_by_user = forms.CharField(label=_("Last modified by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        user_data['status'] = _('active') if self.user.is_active else _('blocked')
        user_data['role_profiles'] = [role_profile.id for role_profile in self.user.role_profiles.all()]
        user_data['application_roles'] = [application_role.id for application_role in
                                          self.user.application_roles.all()]

        if self.user.organisations.count() == 1:
            user_data['organisations'] = self.user.organisations.first()

        initial = kwargs.get('initial', {})
        initial.update(user_data)

        initial['created_by_user'] = self.user.created_by_user if self.user.created_by_user else ''
        initial['last_modified_by_user'] = self.user.last_modified_by_user if self.user.last_modified_by_user else ''

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

        self.fields['application_roles'].choices = []
        app_roles_by_profile = ApplicationRole.objects.filter(roleprofile__user__id=self.user.pk).only("id")
        for application_role in self.request.user.get_administrable_application_roles():
            app_role_text = str(application_role)
            if application_role in app_roles_by_profile:
                app_role_text += " *"
            self.fields['application_roles'].choices.append((application_role.id, app_role_text))
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in
                                                self.request.user.get_administrable_role_profiles()]
        if self.user.organisations.count() > 1:
            self.fields['organisations'] = forms.ModelMultipleChoiceField(
                queryset=None, required=settings.SSO_ORGANISATION_REQUIRED,
                widget=bootstrap.SelectMultipleWithCurrently(
                    currently=', '.join([str(x) for x in self.user.organisations.all()])),
                label=_("Organisation"))
        self.fields['organisations'].queryset = self.request.user.get_administrable_user_organisations(). \
            filter(is_active=True, association__is_selectable=True)

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.exclude(pk=self.user.pk).get(username=username)
        except ObjectDoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def save(self, extend_validity=False, activate=None, remove_org=False, make_member=False):
        cd = self.cleaned_data
        current_user = self.request.user
        if remove_org:
            new_orgs = set()
            removed_orgs = list(self.user.organisations.all())
        else:
            removed_orgs = None
            new_orgs = None

        self.update_user_m2m_fields('organisations', current_user, new_value_set=new_orgs)
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)

        if remove_org:
            self.user.remove_organisation_related_permissions()

        self.user.username = cd['username']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.gender = cd['gender']
        self.user.dob = cd['dob']
        if activate is not None:
            self.user.is_active = activate

        self.create_note_if_required(current_user, cd, activate, extend_validity, removed_orgs)

        if make_member:
            dwbn_member_profile = RoleProfile.objects.get_by_natural_key(uuid=settings.SSO_DEFAULT_MEMBER_PROFILE_UUID)
            self.user.role_profiles.add(dwbn_member_profile)

        if extend_validity or make_member:
            # enable brand specific modification
            valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
            extend_user_validity.send_robust(sender=self.__class__, user=self.user, valid_until=valid_until,
                                             admin=self.request.user)
            self.user.valid_until = valid_until

        self.user.save()

        return self.user


class CenterProfileForm(mixins.UserRolesMixin, mixins.UserNoteMixin, forms.Form):
    """
    Form for SSO Staff for editing Center Accounts
    """
    account_type = bootstrap.ReadOnlyField(label=_("Account type"))
    status = bootstrap.ReadOnlyField(label=_('Status'))
    username = bootstrap.ReadOnlyField(label=_("Username"))
    email = bootstrap.ReadOnlyField(label=_('Email address'))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024,
                            widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    application_roles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Application roles")),
        label=_("Additional application roles"),
        help_text=mixins.UserRolesMixin.application_roles_help)
    role_profiles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.CheckboxSelectMultiple(),
        label=_("Role profiles"),
        help_text=mixins.UserRolesMixin.role_profiles_help)

    created_by_user = forms.CharField(label=_("Created by"), required=False,
                                      widget=bootstrap.TextInput(attrs={'disabled': ''}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        user_data['account_type'] = _('Organisation Account') if self.user.is_center else _('Member Account')
        user_data['status'] = _('active') if self.user.is_active else _('blocked')
        user_data['email'] = force_str(self.user.primary_email())
        user_data['role_profiles'] = [str(role_profile.id) for role_profile in self.user.role_profiles.all()]
        user_data['application_roles'] = [application_role.id for application_role in
                                          self.user.application_roles.all()]
        initial = kwargs.get('initial', {})
        initial.update(user_data)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

        self.fields['application_roles'].choices = []
        app_roles_by_profile = ApplicationRole.objects.filter(roleprofile__user__id=self.user.pk).only("id")
        for application_role in self.request.user.get_administrable_application_roles():
            app_role_text = str(application_role)
            if application_role in app_roles_by_profile:
                app_role_text += " *"
            self.fields['application_roles'].choices.append((application_role.id, app_role_text))

        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in
                                                self.request.user.get_administrable_role_profiles()]

        if self.user.organisations.exists():
            organisation = ', '.join([str(x) for x in self.user.organisations.all()])
            organisation_field = bootstrap.ReadOnlyField(initial=organisation, label=_("Organisation"))
            self.fields['organisation'] = organisation_field

    def save(self, extend_validity=False, activate=None):
        cd = self.cleaned_data
        current_user = self.request.user
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)
        if activate is not None:
            self.user.is_active = activate

        self.create_note_if_required(current_user, cd, activate, extend_validity)

        self.user.save()

        return self.user


class AppAdminUserProfileForm(mixins.UserRolesMixin, forms.Form):
    application_roles = forms.ModelMultipleChoiceField(
        queryset=None, required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Application roles")),
        label=_("Application roles"))
    role_profiles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.CheckboxSelectMultiple(),
        label=_("Role profiles"),
        help_text=mixins.UserRolesMixin.role_profiles_help)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        user_data['role_profiles'] = [str(role_profile.id) for role_profile in self.user.role_profiles.all()]

        initial = kwargs.get('initial', {})
        initial.update(user_data)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

        self.fields['application_roles'].queryset = self.request.user.get_administrable_app_admin_application_roles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in
                                                self.request.user.get_administrable_app_admin_role_profiles()]

    def save(self):
        current_user = self.request.user

        self.update_user_m2m_fields('application_roles', current_user,
                                    admin_attribute_format='get_administrable_app_admin_%s')
        self.update_user_m2m_fields('role_profiles', current_user,
                                    admin_attribute_format='get_administrable_app_admin_%s')

        return self.user
