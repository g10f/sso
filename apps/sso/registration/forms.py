"""
Forms and validation code for user registration.
"""
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from django.forms.models import model_to_dict

from l10n.models import Country
from .models import RegistrationProfile, send_set_password_email
#from sso.registration import default_username_generator

#from sso.forms.bootstrap import StaticInput, CheckboxSelectMultiple
from sso.forms import bootstrap

import logging
logger = logging.getLogger(__name__)

class RegistrationProfileForm(forms.Form):
    """
    Form for organisation and region admins
    """
    error_messages = {
        #'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    
    #username = forms.CharField(label=_("Username"), max_length=30, widget=StaticInput())
    notes = forms.CharField(label=_("Notes"), required=False, max_length=255, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    first_name = forms.CharField(label=_('first name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('e-mail address'), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    phone = forms.CharField(label=_("phone Number"), max_length=30, required=False, widget=bootstrap.TextInput())
    date_registered = forms.DateTimeField(label=_("date registered"), required=False, widget=bootstrap.StaticInput())
    country = forms.CharField(label=_("country"), required=False, max_length=30, widget=bootstrap.StaticInput())
    city = forms.CharField(label=_("city"), required=False, max_length=100, widget=bootstrap.StaticInput())
    postal_code = forms.CharField(label=_("zip code"), required=False, max_length=30, widget=bootstrap.StaticInput())
    street = forms.CharField(label=_('street'), required=False, max_length=255, widget=bootstrap.StaticInput())
    purpose = forms.CharField(label=_('purpose'), required=False, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5, 'readonly': 'readonly'}))
    known_person1 = forms.CharField(label=_("person who can recommend you"), max_length=100, required=False, widget=bootstrap.TextInput())
    known_person2 = forms.CharField(label=_("another person who can recommend you"), max_length=100, required=False, widget=bootstrap.TextInput())
    last_modified_by_user = forms.CharField(label=_("last modified by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    verified_by_user = forms.CharField(label=_("verified by"), required=False, widget=bootstrap.TextInput(attrs={'disabled': ''}))
    is_verified = forms.BooleanField(label=_("is verified"), required=False)    
    organisations = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple, label=_("Application roles"))

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
            logger.error("User without center?", exc_info=1)
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

        if not self.request.user.has_perm('registration.verify_users'):
            self.fields['is_verified'].widget.attrs['disabled'] = True 
        self.fields['application_roles'].queryset = self.request.user.get_inheritable_application_roles()
        self.fields['organisations'].queryset = self.request.user.get_administrable_organisations()

    def save(self, activate=False):
        cd = self.cleaned_data
        
        # registrationprofile data
        self.registrationprofile.notes = cd['notes']
        self.registrationprofile.known_person1 = cd['known_person1']
        self.registrationprofile.known_person2 = cd['known_person2']
        self.registrationprofile.phone = cd['phone']
        if self.request.user.has_perm('registrationprofile.verify_users'):
            self.registrationprofile.verified_by_user = self.request.user if (cd['is_verified'] == True) else None
        
        self.registrationprofile.save()
                
        # userprofile data
        self.user.organisations = [cd.get('organisations')]        
        # update application roles
        new_values = set(cd.get('application_roles').values_list('id', flat=True))
        administrable_values = set(self.request.user.get_inheritable_application_roles().values_list('id', flat=True))
        existing_values = set(self.user.application_roles.all().values_list('id', flat=True))
        
        remove_values = ((existing_values & administrable_values) - new_values)
        add_values = (new_values - existing_values)
        
        if remove_values:
            self.user.application_roles.remove(*remove_values)
        if add_values:
            self.user.application_roles.add(*add_values)
        
        # user data
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']        
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
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    first_name = forms.CharField(label=_('first name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('last name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    purpose = forms.CharField(label=_('purpose'), help_text=_('Which application and information do you like to use?'), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))
    street = forms.CharField(label=_('street'), max_length=255, required=False, widget=bootstrap.TextInput())
    city = forms.CharField(label=_("city"), max_length=100, required=False, widget=bootstrap.TextInput())
    postal_code = forms.CharField(label=_("zip code"), max_length=30, required=False, widget=bootstrap.TextInput())
    known_person1 = forms.CharField(label=_("known person"), max_length=100, widget=bootstrap.TextInput(), 
                                    help_text=_('Please name a person who already has an account and can recommend you.'))
    known_person2 = forms.CharField(label=_("known person #2"), max_length=100, widget=bootstrap.TextInput(), 
                                    help_text=_('Please name another person who already has an account and can recommend you.'))
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label=_("country"), widget=bootstrap.Select())
    phone = forms.CharField(label=_("phone Number"), max_length=30, widget=bootstrap.TextInput())
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['first_name', 'last_name', 'email', 'phone', 
                                'known_person1', 'known_person2',
                                'country', 'postal_code', 'city', 'street', 'purpose']

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            get_user_model().objects.get(email=email)
        except ObjectDoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])

    def save(self, username_generator):
        data = self.cleaned_data
        
        new_user = get_user_model()()
        new_user.username = username_generator(data.get('first_name'), data.get('last_name'))
        new_user.email = data.get('email')
        new_user.first_name = data.get('first_name')
        new_user.last_name = data.get('last_name')        
        new_user.is_active = False
        new_user.set_unusable_password()
        new_user.save()
                
        registration_profile = RegistrationProfile.objects.create(user=new_user)
        registration_profile.purpose = data['purpose']
        registration_profile.phone = data['phone']
        registration_profile.city = data['city']
        registration_profile.known_person1 = data['known_person1']
        registration_profile.known_person2 = data['known_person2']
        registration_profile.country = data['country']
        registration_profile.postal_code = data['postal_code']
        registration_profile.street = data['street']            
        registration_profile.save()
        return registration_profile
