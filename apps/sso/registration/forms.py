"""
Forms and validation code for user registration.
"""
import datetime
import logging
import pytz

from django import forms
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from django.forms.models import model_to_dict
from django.shortcuts import redirect
from formtools.preview import FormPreview
from l10n.models import Country
from .models import RegistrationProfile, send_validation_email
from . import default_username_generator
from sso.forms import bootstrap, mixins, BLANK_CHOICE_DASH
from sso.accounts.models import UserAddress, User
from sso.organisations.models import is_validation_period_active

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
    verified_by_user = forms.CharField(label=_("Verified by"), help_text=_('administrator who verified the user'), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    is_verified = forms.BooleanField(label=_("Is verified"), help_text=_('Designates if the user was verified by another administrator'), required=False)    
    organisations = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select(), required=False)
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple, label=_("Application roles"))
    check_back = forms.BooleanField(label=_("Check back"), help_text=_('Designates if there are open questions to check.'), required=False)    
    is_access_denied = forms.BooleanField(label=_("Access denied"), help_text=_('Designates if access is denied to the user.'), required=False)    
    # role_profiles = forms.ModelMultipleChoiceField(queryset=None, cache_choices=True, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
    #                                               help_text=_('Groups of application roles that are assigned together.'))
    role_profiles = forms.MultipleChoiceField(required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                              help_text=_('Groups of application roles that are assigned together.'))

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
        initial['is_verified'] = True if self.registrationprofile.verified_by_user else False
        verified_by_user = self.registrationprofile.verified_by_user
        initial['verified_by_user'] = verified_by_user if verified_by_user else ''                
        kwargs['initial'] = initial

        super(RegistrationProfileForm, self).__init__(*args, **kwargs)
        current_user = self.request.user
        if not current_user.has_perm('registration.verify_users'):
            self.fields['is_verified'].widget.attrs['disabled'] = True 
        self.fields['application_roles'].queryset = current_user.get_administrable_application_roles()
        # self.fields['role_profiles'].queryset = current_user.get_administrable_role_profiles()
        self.fields['role_profiles'].choices = [(role_profile.id, role_profile) for role_profile in current_user.get_administrable_role_profiles()]
        # add custom data
        self.fields['role_profiles'].dictionary = {str(role_profile.id): role_profile for role_profile in current_user.get_administrable_role_profiles()}

        self.fields['organisations'].queryset = current_user.get_administrable_user_organisations()

    def save(self, activate=False):
        cd = self.cleaned_data
        current_user = self.request.user
        # registrationprofile data
        self.registrationprofile.known_person1_first_name = cd['known_person1_first_name']
        self.registrationprofile.known_person1_last_name = cd['known_person1_last_name']
        self.registrationprofile.known_person2_first_name = cd['known_person2_first_name']
        self.registrationprofile.known_person2_last_name = cd['known_person2_last_name']
        self.registrationprofile.check_back = cd['check_back']
        self.registrationprofile.is_access_denied = cd['is_access_denied']
        if current_user.has_perm('registration.verify_users'):
            self.registrationprofile.verified_by_user = current_user if cd['is_verified'] else None
        
        self.registrationprofile.save()        
        
        # user data
        self.user.username = cd['username']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.notes = cd['notes']
        
        # userprofile data
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)
        self.update_user_m2m_fields('organisations', current_user)
        
        if activate:
            self.user.is_active = True
            self.user.set_password(get_random_string(40))

        organisation = self.cleaned_data['organisations']
        if is_validation_period_active(organisation):
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
    first_name = forms.CharField(label=_('First name'), required=True, max_length=30, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('Last name'), required=True, max_length=30, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    known_person1_first_name = forms.CharField(label=_("First name"), max_length=100, widget=bootstrap.TextInput())
    known_person1_last_name = forms.CharField(label=_("Last name"), max_length=100, widget=bootstrap.TextInput())
    known_person2_first_name = forms.CharField(label=_("First name"), max_length=100, widget=bootstrap.TextInput())
    known_person2_last_name = forms.CharField(label=_("Last name"), max_length=100, widget=bootstrap.TextInput())
    about_me = forms.CharField(label=_('About me'), required=False, help_text=_('If you would like to tell us something about yourself or your involvement with buddhism please do so in this box.'), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label=_("Country"), widget=bootstrap.Select())
    city = forms.CharField(label=_("City"), max_length=100, widget=bootstrap.TextInput())
    language = forms.ChoiceField(label=_("Language"), required=False, choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])), widget=bootstrap.Select())
    timezone = forms.ChoiceField(label=_("Timezone"), required=False, choices=BLANK_CHOICE_DASH + zip(pytz.common_timezones, pytz.common_timezones), widget=bootstrap.Select())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateField(label=_('Date of birth'), required=False, 
                          widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1), required=False))

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            get_user_model().objects.get_by_email(email)
        except ObjectDoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])
    
    def clean(self):
        """
        if the user clicks the edit_again button a ValidationError is raised, to
        display the form again. (see post_post method in FormPreview)
        """
        edit_again = self.data.get("_edit_again")
        if edit_again:
            raise forms.ValidationError('_edit_again', '_edit_again')
        
        return super(UserSelfRegistrationForm, self).clean()
        
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


class UserSelfRegistrationFormPreview(FormPreview):
    form_template = 'registration/registration_form.html'
    preview_template = 'registration/registration_preview.html'

    def get_context(self, request, form):
        """Context for template rendering."""
        context = super(UserSelfRegistrationFormPreview, self).get_context(request, form)
        context.update({'site_name': settings.SSO_SITE_NAME, 'title': _('User registration')})
        return context
    
    @transaction.atomic
    def done(self, request, cleaned_data):
        registration_profile = self.form.save_data(cleaned_data)
        send_validation_email(registration_profile, request)

        return redirect('registration:registration_done')
