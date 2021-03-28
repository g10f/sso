"""
Forms and validation code for user registration.
"""
import datetime
import logging

import pytz

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.utils.text import capfirst
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from l10n.models import Country
from sso.accounts.models import UserAddress, User, UserNote
from sso.forms import bootstrap, mixins, BLANK_CHOICE_DASH
from sso.forms.helpers import clean_base64_picture
from sso.organisations.models import is_validation_period_active
from . import default_username_generator
from .models import RegistrationProfile

logger = logging.getLogger(__name__)


class RegistrationProfileForm(mixins.UserRolesMixin, forms.Form):
    """
    Form for organisation and region admins
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }

    username = forms.CharField(label=_("Username"), max_length=30, widget=bootstrap.TextInput())
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('Email address'), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    date_registered = bootstrap.ReadOnlyField(label=_("Date registered"))
    country = bootstrap.ReadOnlyField(label=_("Country"))
    city = bootstrap.ReadOnlyField(label=_("City"))
    language = bootstrap.ReadOnlyField(label=_("Language"))
    timezone = bootstrap.ReadOnlyField(label=_("Timezone"))
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.CharField(label=_("Date of birth"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    about_me = forms.CharField(label=_('About me'), required=False, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5, 'readonly': 'readonly'}))
    known_person1_first_name = forms.CharField(label=_("First name"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person1_last_name = forms.CharField(label=_("Last name"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person2_first_name = forms.CharField(label=_("First name"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person2_last_name = forms.CharField(label=_("Last name"), max_length=100, required=False, widget=bootstrap.TextInput())
    last_modified_by_user = forms.CharField(label=_("Last modified by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    organisations = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select2(), required=settings.SSO_ORGANISATION_REQUIRED)
    application_roles = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Application roles")),
        label=_("Additional application roles"),
        help_text=mixins.UserRolesMixin.application_roles_help)
    check_back = forms.BooleanField(label=_("Check back"), help_text=_('Designates if there are open questions to check.'), required=False, disabled=True)
    is_access_denied = forms.BooleanField(label=_("Access denied"), help_text=_('Designates if access is denied to the user.'), required=False, disabled=True)
    is_stored_permanently = forms.BooleanField(label=_("Store permanantly"),
                                               help_text=_('Keep stored in database to prevent re-registration of denied user.'), required=False)
    role_profiles = forms.MultipleChoiceField(
        required=False,
        widget=bootstrap.FilteredSelectMultiple(_("Role profiles")),
        label=_("Role profiles"),
        help_text=mixins.UserRolesMixin.role_profiles_help)

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.exclude(pk=self.user.pk).get(username=username)
        except ObjectDoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.registrationprofile = kwargs.pop('instance')
        self.user = self.registrationprofile.user

        registrationprofile_data = model_to_dict(self.registrationprofile)

        user_data = model_to_dict(self.user)
        if self.user.language:
            user_data['language'] = self.user.get_language_display()
        try:
            # after registration, the user should have exactly 1 center
            user_data['organisations'] = self.user.organisations.first()
        except ObjectDoesNotExist:
            # center is optional
            # logger.error("User without center?", exc_info=1)
            pass

        # initialize form correctly
        user_data['role_profiles'] = [str(role_profile.id) for role_profile in self.user.role_profiles.all()]

        address_data = {}
        if self.user.useraddress_set.exists():
            useraddress = self.user.useraddress_set.first()
            address_data = model_to_dict(useraddress)
            address_data['country'] = useraddress.country

        initial = kwargs.get('initial', {})
        initial.update(registrationprofile_data)
        initial.update(user_data)
        initial.update(address_data)

        initial['email'] = self.user.primary_email()
        last_modified_by_user = self.registrationprofile.last_modified_by_user
        initial['last_modified_by_user'] = last_modified_by_user if last_modified_by_user else ''
        kwargs['initial'] = initial

        super().__init__(*args, **kwargs)
        current_user = self.request.user
        self.fields['application_roles'].queryset = current_user.get_administrable_application_roles()
        # self.fields['role_profiles'].queryset = current_user.get_administrable_role_profiles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in
                                                current_user.get_administrable_role_profiles()]
        self.fields['organisations'].queryset = current_user.get_administrable_user_organisations()

    def save(self):
        cd = self.cleaned_data
        current_user = self.request.user
        # registrationprofile data
        self.registrationprofile.known_person1_first_name = cd['known_person1_first_name']
        self.registrationprofile.known_person1_last_name = cd['known_person1_last_name']
        self.registrationprofile.known_person2_first_name = cd['known_person2_first_name']
        self.registrationprofile.known_person2_last_name = cd['known_person2_last_name']

        self.registrationprofile.save()

        # user data
        self.user.username = cd['username']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.is_stored_permanently = cd['is_stored_permanently']

        if cd['notes']:
            UserNote.objects.create_note(user=self.user, notes=[cd['notes']], created_by_user=current_user)

        # userprofile data
        self.update_user_m2m_fields('organisations', current_user)
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)

        organisation = self.cleaned_data['organisations']
        if is_validation_period_active(organisation):
            # a new registered user is valid_until from now for the validation period
            self.user.valid_until = now() + datetime.timedelta(days=settings.SSO_VALIDATION_PERIOD_DAYS)
        self.user.save()

        return self.registrationprofile


class UserSelfRegistrationForm(forms.Form):
    """
    used in for the user self registration
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    first_name = forms.CharField(label=_('First name'), required=True, max_length=30,
                                 widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('Last name'), required=True, max_length=30,
                                widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    base64_picture = forms.CharField(label=_('Your picture'), help_text=_(
        'Please use a photo of your face. We are using it also to validate your registration.'))
    known_person1_first_name = forms.CharField(label=_("First name"), max_length=100, widget=bootstrap.TextInput())
    known_person1_last_name = forms.CharField(label=_("Last name"), max_length=100, widget=bootstrap.TextInput())
    known_person2_first_name = forms.CharField(label=_("First name"), max_length=100, widget=bootstrap.TextInput())
    known_person2_last_name = forms.CharField(label=_("Last name"), max_length=100, widget=bootstrap.TextInput())
    about_me = forms.CharField(label=_('About me'), required=False, help_text=_(
        'If you would like to tell us something about yourself, please do so in this box.'),
                               widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    country = forms.ModelChoiceField(queryset=Country.objects.filter(active=True), label=_("Country"),
                                     widget=bootstrap.Select2())
    city = forms.CharField(label=_("City"), max_length=100, widget=bootstrap.TextInput())
    language = forms.ChoiceField(label=_("Language"), required=False,
                                 choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])),
                                 widget=bootstrap.Select2())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False,
                                 choices=BLANK_CHOICE_DASH + list(zip(pytz.common_timezones, pytz.common_timezones)),
                                 widget=bootstrap.Select2())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES),
                               widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False,
                          widget=bootstrap.SelectDateWidget(
                              years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1)))

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            get_user_model().objects.get_by_email(email)
        except ObjectDoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])

    def clean_base64_picture(self):
        base64_picture = self.cleaned_data["base64_picture"]
        return clean_base64_picture(base64_picture, User.MAX_PICTURE_SIZE)

    def clean(self):
        """
        if the user clicks the edit_again button a ValidationError is raised, to
        display the form again. (see post_post method in FormPreview)
        """
        edit_again = self.data.get("_edit_again")
        if edit_again:
            raise forms.ValidationError('_edit_again', '_edit_again')

        return super().clean()

    @staticmethod
    def save_data(data, username_generator=default_username_generator):

        new_user = get_user_model()()
        new_user.username = username_generator(data.get('first_name'), data.get('last_name'))
        new_user.first_name = data.get('first_name')
        new_user.last_name = data.get('last_name')
        new_user.language = data.get('language')
        new_user.timezone = data.get('timezone')
        new_user.gender = data.get('gender')
        new_user.dob = data.get('dob')
        new_user.is_active = False
        new_user.set_unusable_password()
        if 'base64_picture' in data:
            new_user.picture = data.get('base64_picture')

        new_user.save()

        new_user.create_primary_email(email=data.get('email'))

        user_address = UserAddress()
        user_address.primary = True
        user_address.user = new_user
        user_address.address_type = 'home'
        user_address.country = data['country']
        user_address.city = data['city']
        user_address.addressee = "%s %s" % (data.get('first_name'), data.get('last_name'))
        user_address.save()

        registration_profile = RegistrationProfile.objects.create(user=new_user)
        registration_profile.about_me = data['about_me']
        registration_profile.known_person1_first_name = data['known_person1_first_name']
        registration_profile.known_person1_last_name = data['known_person1_last_name']
        registration_profile.known_person2_first_name = data['known_person2_first_name']
        registration_profile.known_person2_last_name = data['known_person2_last_name']
        registration_profile.save()
        return registration_profile
