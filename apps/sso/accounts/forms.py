# -*- coding: utf-8 -*-
from collections import OrderedDict
import re
import datetime
from mimetypes import guess_extension
import logging

from nocaptcha_recaptcha.fields import NoReCaptchaField
import pytz

from django.utils.timezone import now
from django import forms
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from django.template import loader
from django.core.exceptions import ObjectDoesNotExist
from django.core import signing
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from passwords.fields import PasswordField
from .models import User, UserAddress, UserPhoneNumber, UserEmail, OrganisationChange
from sso.forms.fields import EmailFieldLower
from sso.organisations.models import Organisation, is_validation_period_active
from sso.registration import default_username_generator
from sso.registration.forms import UserSelfRegistrationForm
from sso.forms import bootstrap, mixins, BLANK_CHOICE_DASH, BaseForm


logger = logging.getLogger(__name__)


class OrganisationChangeForm(BaseForm):
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.all().only('id', 'location', 'name', 'country__iso2_code').select_related('country'), label=_("Organisation"), widget=bootstrap.Select())

    class Meta:
        model = OrganisationChange
        fields = ('organisation', 'reason')
        widgets = {
            'reason': bootstrap.Textarea()
        }

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


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=100, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_("Email address"), max_length=75, widget=bootstrap.TextInput())
    subject = forms.CharField(label=_("Subject"), widget=bootstrap.TextInput())
    message = forms.CharField(label=_("Message"), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))


class SetPasswordForm(DjangoSetPasswordForm):
    """
    A form that lets a user change set their password without entering the old
    password.

    When the user has no confirmed emails, then the primary email will be confirmed by save
    """
    new_password1 = PasswordField(label=_("New password"), widget=bootstrap.PasswordInput())
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=bootstrap.PasswordInput())

    def save(self, commit=True):
        self.user = super(SetPasswordForm, self).save(commit)
        self.user.confirm_primary_email_if_no_confirmed()

        return self.user


class PasswordChangeForm(DjangoSetPasswordForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    old_password = forms.CharField(label=_("Old password"), widget=bootstrap.PasswordInput())
    new_password1 = PasswordField(label=_("New password"), widget=bootstrap.PasswordInput())
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
             from_email=None, request=None, html_email_template_name=None):
        email = self.cleaned_data["email"]
        current_site = get_current_site(request)
        site_name = settings.SSO_SITE_NAME
        domain = current_site.domain

        user = User.objects.get_by_confirmed_or_primary_email(email)

        # Make sure that no email is sent to a user that actually has
        # a password marked as unusable
        if not user.has_usable_password():
            logger.error("user has unusable password")
        expiration_date = now() + datetime.timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
        c = {
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
        user.email_user(subject, message, from_email)


class SetPictureAndPasswordForm(SetPasswordForm):
    """
    for new created users with an optional picture field
    """
    picture = forms.ImageField(label=_('Profile picture'), required=False, widget=bootstrap.ImageWidget())

    def clean_picture(self):
        from django.template.defaultfilters import filesizeformat
        max_upload_size = User.MAX_PICTURE_SIZE  # 5 MB
        picture = self.cleaned_data["picture"]
        if picture and hasattr(picture, 'content_type'):
            base_content_type = picture.content_type.split('/')[0]
            if base_content_type in ['image']:
                if picture._size > max_upload_size:
                    raise forms.ValidationError(_('Please keep filesize under %(filesize)s. Current filesize %(current_filesize)s') %
                                                {'filesize': filesizeformat(max_upload_size), 'current_filesize': filesizeformat(picture._size)})
                # mimetypes.guess_extension return jpe which is quite uncommon for jpeg
                if picture.content_type == 'image/jpeg':
                    file_ext = '.jpg'
                else:
                    file_ext = guess_extension(picture.content_type)
                picture.name = "%s%s" % (get_random_string(7, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'), file_ext)
            else:
                raise forms.ValidationError(_('File type is not supported'))
        return picture

    def save(self, commit=True):
        cd = self.cleaned_data
        if 'picture' in self.changed_data:
            self.user.picture.delete(save=False)
        self.user.picture = cd['picture'] if cd['picture'] else None

        self.user = super(SetPictureAndPasswordForm, self).save(commit)
        return self.user


class AdminUserCreationForm(forms.ModelForm):
    """
    Django Admin Site UserCreationForm where no password is required and the username is created from first_name and last_name
    If the password is empty, an random password is created
    """
    password1 = forms.CharField(label=_("Password"), required=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), required=False, widget=forms.PasswordInput, help_text=_("Enter the same password as above, for verification."))
    first_name = forms.CharField(label=_('First name'), required=True)
    last_name = forms.CharField(label=_('Last name'), required=True)

    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def clean(self):
        cleaned_data = super(AdminUserCreationForm, self).clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError(self.error_messages['password_mismatch'])

    def save(self, commit=True):
        user = super(AdminUserCreationForm, self).save(commit=False)
        password = self.cleaned_data.get("password1", "")
        if password == "":
            password = get_random_string(40)
        user.set_password(password)

        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')), capfirst(self.cleaned_data.get('last_name')))

        if commit:
            user.save()
        return user


class AdminUserChangeForm(UserChangeForm):
    """
    extensions to the default form:
    - allow also unicode characters in the username
    """
    username = forms.RegexField(
        label=_("Username"), max_length=30, regex=re.compile(r"^[\w.@+-]+$", flags=re.UNICODE),
        help_text=_("Required. 30 characters or fewer. Letters, digits and "
                    "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})


class UserAddForm(forms.ModelForm):
    """
    form for SSO User Admins for adding users in the frontend
    """
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    first_name = forms.CharField(label=_('First name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('Last name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    gender = forms.ChoiceField(label=_('Gender'), required=True, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False,
                          widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1), required=False))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    organisation = forms.ModelChoiceField(queryset=None, required=False, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))
    role_profiles = forms.MultipleChoiceField(required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                              help_text=_('Groups of application roles that are assigned together.'))

    error_messages = {
        'duplicate_email': _("A user with that email address already exists."),
    }

    class Meta:
        model = User
        fields = ("first_name", "last_name", 'gender', 'dob', 'notes')

    def __init__(self, user, *args, **kwargs):
        super(UserAddForm, self).__init__(*args, **kwargs)
        self.fields['application_roles'].queryset = user.get_administrable_application_roles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in user.get_administrable_role_profiles()]
        # add custom data
        self.fields['role_profiles'].dictionary = {str(role_profile.id): role_profile for role_profile in user.get_administrable_role_profiles()}
        self.fields['organisation'].queryset = user.get_administrable_user_organisations()
        if not user.has_perm("accounts.access_all_users"):
            self.fields['organisation'].required = True

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
        user = super(UserAddForm, self).save(commit=False)
        user.set_password(get_random_string(40))
        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')), capfirst(self.cleaned_data.get('last_name')))

        organisation = self.cleaned_data["organisation"]
        if is_validation_period_active(organisation):
            user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        user.save()

        user.application_roles = self.cleaned_data["application_roles"]
        user.role_profiles = self.cleaned_data["role_profiles"]
        if organisation:
            user.organisations.add(organisation)

        user.create_primary_email(email=self.cleaned_data["email"])
        return user


class AddressForm(BaseForm):
    class Meta:
        model = UserAddress
        fields = ('primary', 'address_type', 'addressee', 'street_address', 'city', 'city_native', 'postal_code', 'country', 'region')
        widgets = {
            'primary': bootstrap.CheckboxInput(),
            'address_type': bootstrap.Select(),
            'addressee': bootstrap.TextInput(attrs={'size': 50}),
            'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
            'city': bootstrap.TextInput(attrs={'size': 50}),
            'city_native': bootstrap.TextInput(attrs={'size': 50}),
            'postal_code': bootstrap.TextInput(attrs={'size': 50}),
            'country': bootstrap.Select(),
            'region': bootstrap.TextInput(attrs={'size': 50}),
        }
    
    @staticmethod
    def template():
        return 'edit_inline/stacked.html'


class PhoneNumberForm(BaseForm):
    class Meta:
        model = UserPhoneNumber
        fields = ('phone_type', 'phone', 'primary') 
        widgets = {
            'phone_type': bootstrap.Select(),
            'phone': bootstrap.TextInput(attrs={'size': 50}),
            'primary': bootstrap.CheckboxInput()
        }
    
    @staticmethod
    def template():
        return 'edit_inline/tabular.html'


class SelfUserEmailForm(forms.Form):
    email = EmailFieldLower(max_length=254, label=_('Email address'), required=True)
    user = forms.IntegerField(widget=forms.HiddenInput())

    error_messages = {
        'duplicate_email': _("The email address \"%(email)s\" is already in use."),
    }

    def clean(self):
        cleaned_data = super(SelfUserEmailForm, self).clean()
        if 'email' in cleaned_data:
            email = cleaned_data["email"]
            qs = UserEmail.objects.filter(email=email)
            if qs.exists():
                raise forms.ValidationError(self.error_messages['duplicate_email'] % {'email': email})

    def save(self):
        cd = self.cleaned_data
        user_email = UserEmail(email=cd['email'], user_id=cd['user'])
        user_email.save()
        return user_email


class UserEmailForm(BaseForm):

    class Meta:
        model = UserEmail
        fields = ('email', 'primary', 'confirmed')
        widgets = {
            'email': bootstrap.EmailInput(),
            'primary': bootstrap.CheckboxInput(),
            'confirmed': bootstrap.CheckboxInput()
        }

    @staticmethod
    def template():
        return 'edit_inline/tabular.html'


class UserSelfProfileForm(forms.Form):
    """
    Form for the user himself to change editable values
    """
    username = bootstrap.ReadOnlyField(label=_("Username"))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    picture = forms.ImageField(label=_('Picture'), required=False, widget=bootstrap.ImageWidget())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False, 
                          widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1), required=False))
    homepage = forms.URLField(label=_('Homepage'), required=False, max_length=512, widget=bootstrap.TextInput())
    language = forms.ChoiceField(label=_("Language"), required=False, choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])), widget=bootstrap.Select())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False, choices=BLANK_CHOICE_DASH + zip(pytz.common_timezones, pytz.common_timezones), widget=bootstrap.Select())

    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        initial = kwargs.get('initial', {})
        object_data.update(initial)   
        kwargs['initial'] = object_data
        super(UserSelfProfileForm, self).__init__(*args, **kwargs)

        organisation_field = bootstrap.ReadOnlyField(initial=u', '.join([x.__unicode__() for x in self.user.organisations.all()]),
                                                     label=_("Organisation"), help_text=_('Please use the contact form for a request to change this value.'))
        self.fields['organisation'] = organisation_field

    def clean_organisation(self):
        if self.user.organisations.exists():
            # if already assigned to an organisation return None, (readonly use case)
            return None
        else:
            return self.cleaned_data['organisation'] 

    def clean_picture(self):
        from django.template.defaultfilters import filesizeformat
        max_upload_size = User.MAX_PICTURE_SIZE  # 5 MB
        picture = self.cleaned_data["picture"]
        if picture and hasattr(picture, 'content_type'):
            base_content_type = picture.content_type.split('/')[0]
            if base_content_type in ['image']:
                if picture._size > max_upload_size:
                    raise forms.ValidationError(_('Please keep filesize under %(filesize)s. Current filesize %(current_filesize)s') %
                                                {'filesize': filesizeformat(max_upload_size), 'current_filesize': filesizeformat(picture._size)})
                # mimetypes.guess_extension return jpe which is quite uncommon for jpeg
                if picture.content_type == 'image/jpeg':
                    file_ext = '.jpg'
                else:
                    file_ext = guess_extension(picture.content_type)
                picture.name = "%s%s" % (get_random_string(7, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'), file_ext)
            else:
                raise forms.ValidationError(_('File type is not supported'))
        return picture
    
    def save(self):
        cd = self.cleaned_data
        if (not self.initial['first_name'] and not self.initial['last_name']) and cd.get('first_name') and cd.get('last_name'):            
            # should be a streaming user, which has no initial first_name and last_name
            # we create the new username because the streaming user has his email as username
            self.user.username = default_username_generator(capfirst(cd.get('first_name')), capfirst(cd.get('last_name')))
            
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
            self.user.organisations.add(cd['organisation']) 
        

class CenterSelfProfileForm(forms.Form):
    """
    Form for a user which represents a center
    """
    account_type = bootstrap.ReadOnlyField(label=_("Account type"))
    username = bootstrap.ReadOnlyField(label=_("Username"))
    first_name = bootstrap.ReadOnlyField(label=_('First name'))
    last_name = bootstrap.ReadOnlyField(label=_('Last name'))
    email = bootstrap.ReadOnlyField(label=_('Email address'))
    language = forms.ChoiceField(label=_("Language"), required=False, choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])), widget=bootstrap.Select())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False, choices=BLANK_CHOICE_DASH + zip(pytz.common_timezones, pytz.common_timezones), widget=bootstrap.Select())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        object_data['account_type'] = _('Organisation Account') if self.user.is_center else _('Member Account')
        object_data['email'] = str(self.user.primary_email())
        initial = kwargs.get('initial', {})
        object_data.update(initial)
        kwargs['initial'] = object_data
        super(CenterSelfProfileForm, self).__init__(*args, **kwargs)

        if self.user.organisations.exists():
            organisation = u', '.join([x.__unicode__() for x in self.user.organisations.all()])
            organisation_field = bootstrap.ReadOnlyField(initial=organisation, label=_("Organisation"))
            self.fields['organisation'] = organisation_field

    def save(self):
        cd = self.cleaned_data
        self.user.language = cd['language']
        self.user.timezone = cd['timezone']
        self.user.save()
        

class UserSelfProfileDeleteForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        super(UserSelfProfileDeleteForm, self).__init__(*args, **kwargs)
        
    def save(self):
        self.user.is_active = False
        self.user.save()
            
    
class UserSelfRegistrationForm2(UserSelfRegistrationForm):
    """
    Overwritten UserSelfRegistrationForm Form with additional  organisation field
    """
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.all().select_related('country'), required=False, label=_("Organisation"), widget=bootstrap.Select())
    # for Bots. If you enter anything in this field you will be treated as a robot
    state = forms.CharField(label=_('State'), required=False, widget=bootstrap.HiddenInput())
    
    signer = signing.TimestampSigner()

    def __init__(self, data=None, *args, **kwargs):
        super(UserSelfRegistrationForm2, self).__init__(data, *args, **kwargs)
        
        if self.is_captcha_needed():
            self.fields['captcha'] = NoReCaptchaField()
            #                help_text=_('Please enter the words you see in the box, in order and separated by a space. Doing so helps prevent automated programs from abusing this service.'),
            #                error_messages={'captcha_invalid': _('Incorrect, please try again.')}, attrs={'theme': 'clean'})

    def is_captcha_needed(self):
        max_age = 300
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
        return super(UserSelfRegistrationForm2, self).clean()
    
    """
    def clean_state(self):
        # Honey pot field for bots, can be used instead of a captcha
        state = self.cleaned_data.get('state')
        if state:
            # is invisible, if it is filled, this must be a bot
            raise forms.ValidationError('wrong value')
        return state
    """
    
    @staticmethod
    def save_data(data, username_generator=default_username_generator):
        registration_profile = UserSelfRegistrationForm.save_data(data, username_generator)
        new_user = registration_profile.user
        
        default_role_profile = User.get_default_role_profile()
        if default_role_profile:
            new_user.role_profiles.add(default_role_profile)

        organisation = data["organisation"]
        if organisation:
            new_user.organisations.add(data["organisation"])
        return registration_profile


class UserProfileForm(mixins.UserRolesMixin, forms.Form):
    """
    Form for SSO Staff
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    username = forms.CharField(label=_("Username"), max_length=30, widget=bootstrap.TextInput())
    valid_until = bootstrap.ReadOnlyField(label=_("Valid until"))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False,
                          widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1), required=False))
    is_active = forms.BooleanField(label=_('Active'), help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'),
                                   widget=bootstrap.CheckboxInput(), required=False)
    is_center = forms.BooleanField(label=_('Organisation'), help_text=_('Designates that this user is representing a organisation and not a private person.'),
                                   widget=bootstrap.CheckboxInput(), required=False)
    organisations = forms.ModelChoiceField(queryset=None, required=False, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    role_profiles = forms.MultipleChoiceField(required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                              help_text=_('Groups of application roles that are assigned together.'))

    extend_validity = forms.BooleanField(label=_('Extend validity'), widget=bootstrap.CheckboxInput(), required=False)
    created_by_user = forms.CharField(label=_("Created by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        try:
            # the user should have exactly 1 center 
            user_data['organisations'] = self.user.organisations.first()
        except ObjectDoesNotExist:
            # center is optional
            # logger.error("User without center?", exc_info=1)
            pass
        
        initial = kwargs.get('initial', {})
        initial.update(user_data)

        created_by_user = self.user.created_by_user
        initial['created_by_user'] = created_by_user if created_by_user else ''

        kwargs['initial'] = initial
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.fields['application_roles'].queryset = self.request.user.get_administrable_application_roles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in self.request.user.get_administrable_role_profiles()]
        # add custom data
        self.fields['role_profiles'].dictionary = {str(role_profile.id): role_profile for role_profile in self.request.user.get_administrable_role_profiles()}

        self.fields['organisations'].queryset = self.request.user.get_administrable_user_organisations()

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.exclude(pk=self.user.pk).get(username=username)
        except ObjectDoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def save(self):
        cd = self.cleaned_data
        current_user = self.request.user
        
        if cd['extend_validity']:
            self.user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        self.user.username = cd['username']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.gender = cd['gender']
        self.user.dob = cd['dob']
        self.user.is_active = cd['is_active']
        self.user.is_center = cd['is_center']
        self.user.notes = cd['notes']
        self.user.save()

        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)
        self.update_user_m2m_fields('organisations', current_user)

        return self.user


class AppAdminUserProfileForm(mixins.UserRolesMixin, forms.Form):
    """
    Form for application admins and profile admins
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    username = bootstrap.ReadOnlyField(label=_("Username"))
    first_name = bootstrap.ReadOnlyField(label=_("First name"))
    last_name = bootstrap.ReadOnlyField(label=_("Last name"))
    email = bootstrap.ReadOnlyField(label=_("Email"))
    organisations = bootstrap.ReadOnlyField(label=_("Organisation"))
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))
    role_profiles = forms.MultipleChoiceField(required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                              help_text=_('Groups of application roles that are assigned together.'))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        user_data['email'] = self.user.primary_email()
        user_data['organisations'] = u', '.join([x.__unicode__() for x in self.user.organisations.all()])

        initial = kwargs.get('initial', {})
        initial.update(user_data)
        kwargs['initial'] = initial
        super(AppAdminUserProfileForm, self).__init__(*args, **kwargs)

        self.fields['application_roles'].queryset = self.request.user.get_administrable_application_roles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in self.request.user.get_administrable_role_profiles()]
        # add custom data
        self.fields['role_profiles'].dictionary = {str(role_profile.id): role_profile for role_profile in self.request.user.get_administrable_role_profiles()}

    def save(self):
        cd = self.cleaned_data
        current_user = self.request.user

        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)

        return self.user
