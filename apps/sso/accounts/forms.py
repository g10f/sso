# -*- coding: utf-8 -*-
import re
from django import forms 

from django.conf import settings
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from django.template import loader
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.sites.models import get_current_site
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.tokens import default_token_generator

from passwords.fields import PasswordField
from .models import Organisation
from sso.registration import default_username_generator
from sso.registration.forms import UserRegistrationCreationForm
from sso.forms import bootstrap

import logging
logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=100, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_("e-mail address"), max_length=75, widget=bootstrap.TextInput())
    subject = forms.CharField(label=_("Subject"), widget=bootstrap.TextInput())
    message = forms.CharField(label=_("Message"), widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 5}))


class SetPasswordForm(DjangoSetPasswordForm):
    new_password1 = PasswordField(label=_("New password"), widget=bootstrap.PasswordInput())
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=bootstrap.PasswordInput())


class PasswordChangeForm(SetPasswordForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
    })
    old_password = forms.CharField(label=_("Old password"), widget=bootstrap.PasswordInput())

    def clean_old_password(self):
        """
        Validates that the old_password field is correct.
        """
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                self.error_messages['password_incorrect'])
        return old_password
PasswordChangeForm.base_fields.keyOrder = ['old_password', 'new_password1', 'new_password2']


class PasswordResetForm(DjangoPasswordResetForm):
    """
    allow unusable passwords, because we want to create a user with no password
    and the user has to change the password with the password reset feature
    """
    error_messages = {
        'unknown': _("That email address doesn't have an associated "
                     "user account. Are you sure you've registered?"),
        'unusable': _("The user account associated with this email "
                      "address cannot reset the password."),
    }
    email = forms.EmailField(label=_("Email"), max_length=254, widget=bootstrap.EmailInput())

    def __init__(self, *args, **kwargs):
        self.password = None
        super(PasswordResetForm, self).__init__(*args, **kwargs)       
    
    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        self.users_cache = get_user_model().objects.filter(email__iexact=email, is_active=True)
        if not len(self.users_cache):
            if ('streaming.backends.StreamingBackend' in settings.AUTHENTICATION_BACKENDS):
                # check if the user exist in the streaming db
                from streaming.models import StreamingUser
                try:
                    streaming_user = StreamingUser.objects.get(email=email)
                    self.password = streaming_user.password.decode("base64")
                    return email
                except ObjectDoesNotExist:
                    pass
                except Exception, e:
                    logger.exception(e)
                
            raise forms.ValidationError(self.error_messages['unknown'])
        return email
    
    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        
        if (not self.password):
            # use parent method
            super(PasswordResetForm, self).save(domain_override, subject_template_name, email_template_name, use_https, token_generator, from_email, request)
        else:
            from django.core.mail import send_mail
            email = self.cleaned_data["email"]
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            c = {
                'email': email,
                'password': self.password,
                'domain': domain,
                'site_name': site_name,
            }
            subject = loader.render_to_string('streaming/password_resend_subject.txt', c)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            message = loader.render_to_string('streaming/password_resend_email.html', c)
            send_mail(subject, message, from_email, [email])

"""
def _username_placeholder():
    first_name = capfirst(_('first name').replace(' ', ''))
    last_name = capfirst(_('last name').replace(' ', ''))
    return u''.join([first_name, last_name])
username_placeholder = lazy(_username_placeholder, unicode)
"""


class UserCreationForm(forms.ModelForm):
    """
    UserCreationForm where no password is required
    If the password is empty, an empty password is created
    """
    password1 = PasswordField(label=_("Password"), required=False, widget=bootstrap.PasswordInput())
    password2 = forms.CharField(label=_("Password confirmation"), required=False, widget=bootstrap.PasswordInput(),
        help_text=_("Enter the same password as above, for verification."))
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'password_mismatch': _("The two password fields didn't match."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    email = forms.EmailField(label=_('Email'), required=True, widget=bootstrap.EmailInput())
    first_name = forms.CharField(label=_('first name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('last name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.get(username=username)
        except ObjectDoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def clean_email(self):
        # Check if email is unique,
        email = self.cleaned_data["email"]
        try:
            get_user_model().objects.get(email__iexact=email)
        except ObjectDoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'])
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data.get("password1", ""))
        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')), capfirst(self.cleaned_data.get('last_name')))
        if commit:
            user.save()
        return user


class UserCreationForm2(UserCreationForm):
    """
    UserCreationForm with organisations select element
    """
    organisation = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))

    def __init__(self, user, *args, **kwargs):
        super(UserCreationForm2, self).__init__(*args, **kwargs)
        self.fields['application_roles'].queryset = user.get_inheritable_application_roles()
        self.fields['organisation'].queryset = user.get_administrable_organisations()
        self.fields.keyOrder = ['first_name', 'last_name', 'email', 'organisation', 'application_roles']  # , 'password1', 'password2']
    

class UserUserProfileForm(forms.Form):
    """
    Form for the user himself to change editable values
    """
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        initial = kwargs.get('initial', {})
        object_data.update(initial)   
        kwargs['initial'] = object_data
        super(UserUserProfileForm, self).__init__(*args, **kwargs)

        # if the user is already in at least 1 organisation, 
        # the organisation field is readonly
        # otherwise a required select field is displayed 
        organisation_field = None
        if self.user.organisations.exists():
            organisation = u', '.join([x.__unicode__() for x in self.user.organisations.all()])
            organisation_field = forms.CharField(required=False, initial=organisation, label=_("Center"), 
                                                help_text=_('Please use the contact form for a request to change this value.'), widget=bootstrap.StaticInput())
        else:
            organisation_field = forms.ModelChoiceField(queryset=Organisation.objects.all(), label=_("Center"), widget=bootstrap.Select(), 
                                                help_text=_('You can set this value only once.'))
        if organisation_field:
            self.fields['organisation'] = organisation_field
        
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    username = forms.CharField(label=_("Username"), max_length=30, required=False, widget=bootstrap.StaticInput())
    organisation = forms.Field()  # place holder for field order when dynamically inserting organisation in __init__
    first_name = forms.CharField(label=_('first name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('e-mail address'), widget=bootstrap.EmailInput())
    picture = forms.ImageField(label=_('picture'), required=False, widget=bootstrap.ImageWidget())
    
    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(self.error_messages['duplicate_email'])
        return email
    
    def clean_organisation(self):
        if self.user.organisations.exists():
            # if already assigned to an organisation return None, (readonly use case)
            return None
        else:
            return self.cleaned_data['organisation'] 

    def clean_picture(self):
        from django.template.defaultfilters import filesizeformat
        MAX_UPLOAD_SIZE = 5242880  # 5 MB
        picture = self.cleaned_data["picture"]
        if picture and hasattr(picture, 'content_type'):
            content_type = picture.content_type.split('/')[0]
            if content_type in ['image']:
                if picture._size > MAX_UPLOAD_SIZE:
                    raise forms.ValidationError(_('Please keep filesize under %(filesize)s. Current filesize %(current_filesize)s') % \
                                                {'filesize': filesizeformat(MAX_UPLOAD_SIZE), 'current_filesize': filesizeformat(picture._size)})
            else:
                raise forms.ValidationError(_('File type is not supported'))
        return picture
    
    def save(self):
        cd = self.cleaned_data
        if (not self.initial['first_name'] and not self.initial['last_name']) and cd.get('first_name') and cd.get('last_name'):            
            # should be a streaming user, which has no initial first_name and last_name
            # we create the new username because the streaming user has his email as username
            self.user.username = default_username_generator(capfirst(cd.get('first_name')), capfirst(cd.get('last_name')))
            
        self.user.email = cd['email']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.picture = cd['picture'] if cd['picture'] else None
        self.user.save()
        
        organisation = cd.get('organisation')
        if organisation:
            # user selected an organisation, this can only happen if the user before had
            # no organisation (see clean_organisation).
            # This can be with streaming accounts. We add automatically standard Roles  
            self.user.organisations.add(cd['organisation'])
            self.user.add_standard_roles()  
        
        
class BasicUserChangeForm(forms.ModelForm):
    class Meta:
        model = get_user_model()

    error_messages = {
        'duplicate_email': _("That email address is already in use."),
    }

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(self.error_messages['duplicate_email'])
        return email


class AdminUserChangeForm(UserChangeForm, BasicUserChangeForm):
    """
    extensions to the default form:
    - allow also unicode characters in the username
    - check if email is unique
    """
    username = forms.RegexField(
        label=_("Username"), max_length=30, regex=re.compile(r"^[\w.@+-]+$", flags=re.UNICODE),
        help_text=_("Required. 30 characters or fewer. Letters, digits and "
                      "@/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and "
                         "@/./+/-/_ characters.")})
    
    def _get_validation_exclusions(self):
        """
        exclude username from model validation, because the model does not allow unicode chars
        """
        exclude = super(AdminUserChangeForm, self)._get_validation_exclusions()
        exclude.append('username')
        return exclude    

    class Meta:
        model = get_user_model()


class UserRegistrationCreationForm2(UserRegistrationCreationForm):
    """
    Overwritten UserRegistrationCreationForm Form with additional  organisation field
    """
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.all(), label=_("Center"), widget=bootstrap.Select())
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationCreationForm2, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['first_name', 'last_name', 'email', 'phone', 'organisation', 
                                'known_person1', 'known_person2',
                                'country', 'postal_code', 'city', 'street', 'purpose']

    def save(self, username_generator):
        registration_profile = super(UserRegistrationCreationForm2, self).save(username_generator)
        user = registration_profile.user
        user.organisations.add(self.cleaned_data["organisation"])
        return registration_profile


class UserProfileForm(forms.Form):
    """
    Form for organisation and region admins
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    
    #username = forms.CharField(label=_("Username"), max_length=30, required=False, widget=bootstrap.StaticInput())
    first_name = forms.CharField(label=_('first name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('e-mail address'), widget=bootstrap.EmailInput())
    is_active = forms.BooleanField(label=_('active'), help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'), required=False)
    organisations = forms.ModelChoiceField(queryset=None, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        try:
            # the user should have exactly 1 center 
            user_data['organisations'] = self.user.organisations.all()[0]
        except IndexError:
            logger.error("User without center?", exc_info=1)
            pass
        
        initial = kwargs.get('initial', {})
        initial.update(user_data)
        kwargs['initial'] = initial
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.fields['application_roles'].queryset = self.request.user.get_inheritable_application_roles()
        self.fields['organisations'].queryset = self.request.user.get_administrable_organisations()

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(self.error_messages['duplicate_email'])
        return email

    def save(self):
        cd = self.cleaned_data
        if (not self.initial['first_name'] and not self.initial['last_name']) and cd.get('first_name') and cd.get('last_name'):            
            # should be a streaming user, which has no initial first_name and last_name
            # we create the new username because the streaming user has his email as username
            self.user.username = default_username_generator(capfirst(cd.get('first_name')), capfirst(cd.get('last_name')))
            
        self.user.email = cd['email']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.is_active = cd['is_active']
        
        self.user.save()
        
        # update organisations
        #self.userprofile.organisations = [cd.get('organisations')]        

        new_values = set([cd.get('organisations').id])  # set(cd.get('organisations').values_list('id', flat=True))
        administrable_values = set(self.request.user.get_administrable_organisations().values_list('id', flat=True))
        existing_values = set(self.user.organisations.all().values_list('id', flat=True))
        
        remove_values = ((existing_values & administrable_values) - new_values)
        add_values = (new_values - existing_values)
        
        if remove_values:
            self.user.organisations.remove(*remove_values)
        if add_values:
            self.user.organisations.add(*add_values)
        
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

        return self.user
