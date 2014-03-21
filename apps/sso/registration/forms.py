"""
Forms and validation code for user registration.
"""
from django import forms
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.contrib.formtools.preview import FormPreview
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from django.forms.models import model_to_dict
from django.shortcuts import redirect

from l10n.models import Country
from .models import RegistrationProfile, send_set_password_email, send_validation_email
from . import default_username_generator

from sso.forms import bootstrap, mixins

import logging
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
    first_name = forms.CharField(label=_('first name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('e-mail address'), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    phone = forms.CharField(label=_("phone Number"), max_length=30, required=False, widget=bootstrap.TextInput())
    date_registered = forms.DateTimeField(label=_("date registered"), required=False, widget=bootstrap.StaticInput())
    country = forms.CharField(label=_("country"), required=False, max_length=30, widget=bootstrap.StaticInput())
    city = forms.CharField(label=_("city"), required=False, max_length=100, widget=bootstrap.StaticInput())
    postal_code = forms.CharField(label=_("zip code"), required=False, max_length=30, widget=bootstrap.StaticInput())
    street = forms.CharField(label=_('street'), required=False, max_length=255, widget=bootstrap.StaticInput())
    about_me = forms.CharField(label=_('about me'), required=False, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5, 'readonly': 'readonly'}))
    known_person1_first_name = forms.CharField(label=_("first name"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person1_last_name = forms.CharField(label=_("last name"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person2_first_name = forms.CharField(label=_("first name #2"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person2_last_name = forms.CharField(label=_("last name #2"), max_length=100, required=False, widget=bootstrap.TextInput())
    last_modified_by_user = forms.CharField(label=_("last modified by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    verified_by_user = forms.CharField(label=_("verified by"), help_text=_('administrator who verified the user'), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    is_verified = forms.BooleanField(label=_("is verified"), help_text=_('Designates if the user was verified by another administrator'), required=False)    
    organisations = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select(), required=False)
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple, label=_("Application roles"))
    check_back = forms.BooleanField(label=_("check back"), help_text=_('Designates if there are open questions to check.'), required=False)    
    is_access_denied = forms.BooleanField(label=_("access denied"), help_text=_('Designates if access is denied to the user.'), required=False)    
    role_profiles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
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
        registrationprofile_data['country'] = self.registrationprofile.country
        
        user_data = model_to_dict(self.user)
        try:
            # after registration, the user should have exactly 1 center 
            user_data['organisations'] = self.user.organisations.all()[0]
        except IndexError:
            # center is optional
            #logger.error("User without center?", exc_info=1)
            pass
            
        initial = kwargs.get('initial', {})
        initial.update(registrationprofile_data)
        initial.update(user_data)
        
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
        self.fields['role_profiles'].queryset = current_user.get_administrable_role_profiles()
        self.fields['organisations'].queryset = current_user.get_administrable_organisations()

    def save(self, activate=False):
        cd = self.cleaned_data
        current_user = self.request.user
        # registrationprofile data
        self.registrationprofile.known_person1_first_name = cd['known_person1_first_name']
        self.registrationprofile.known_person1_last_name = cd['known_person1_last_name']
        self.registrationprofile.known_person2_first_name = cd['known_person2_first_name']
        self.registrationprofile.known_person2_last_name = cd['known_person2_last_name']
        self.registrationprofile.phone = cd['phone']
        self.registrationprofile.check_back = cd['check_back']
        self.registrationprofile.is_access_denied = cd['is_access_denied']
        if current_user.has_perm('registrationprofile.verify_users'):
            self.registrationprofile.verified_by_user = current_user if (cd['is_verified'] == True) else None
        
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
            send_set_password_email(self.user, self.request)
        self.user.save()

        return self.registrationprofile


class UserRegistrationCreationForm(forms.Form):
    """
    used in for the user self registration
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    first_name = forms.CharField(label=_('first name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('last name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    known_person1_first_name = forms.CharField(label=_("first name"), max_length=100, widget=bootstrap.TextInput())
    known_person1_last_name = forms.CharField(label=_("last name"), max_length=100, widget=bootstrap.TextInput())
    known_person2_first_name = forms.CharField(label=_("first name #2"), max_length=100, widget=bootstrap.TextInput())
    known_person2_last_name = forms.CharField(label=_("last name #2"), max_length=100, widget=bootstrap.TextInput())
    about_me = forms.CharField(label=_('about me'), required=False, help_text=_('If you would like to tell us something about yourself or your involvement with buddhism please do so in this box.'), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label=_("country"), widget=bootstrap.Select())
    city = forms.CharField(label=_("city"), max_length=100, widget=bootstrap.TextInput())

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            get_user_model().objects.get(email=email)
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
        
        return super(UserRegistrationCreationForm, self).clean()
        
    @staticmethod
    def save_data(data, username_generator=default_username_generator):

        new_user = get_user_model()()
        new_user.username = username_generator(data.get('first_name'), data.get('last_name'))
        new_user.email = data.get('email')
        new_user.first_name = data.get('first_name')
        new_user.last_name = data.get('last_name')        
        new_user.is_active = False
        new_user.set_unusable_password()
        new_user.save()
                
        registration_profile = RegistrationProfile.objects.create(user=new_user)
        registration_profile.about_me = data['about_me']
        registration_profile.city = data['city']
        registration_profile.known_person1_first_name = data['known_person1_first_name']
        registration_profile.known_person1_last_name = data['known_person1_last_name']
        registration_profile.known_person2_first_name = data['known_person2_first_name']
        registration_profile.known_person2_last_name = data['known_person2_last_name']
        registration_profile.country = data['country']
        registration_profile.save()
        return registration_profile


class UserRegistrationCreationFormPreview(FormPreview):
    form_template = 'registration/registration_form.html'
    preview_template = 'registration/registration_preview.html'

    def get_context(self, request, form):
        "Context for template rendering."
        context = super(UserRegistrationCreationFormPreview, self).get_context(request, form)
        context.update({'site_name': settings.SSO_CUSTOM['SITE_NAME'], 'title': _('User registration')})
        return context
    
    @transaction.atomic
    def done(self, request, cleaned_data):
        registration_profile = self.form.save_data(cleaned_data)
        send_validation_email(registration_profile, request)

        return redirect('registration:registration_done')
