# -*- coding: utf-8 -*-
import re
import datetime

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
from django.contrib.sites.models import get_current_site
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.tokens import default_token_generator

from captcha.fields import ReCaptchaField
from passwords.fields import PasswordField
from .models import User, UserAddress, UserPhoneNumber, UserAssociatedSystem
from sso.organisations.models import Organisation
from sso.registration import default_username_generator
from sso.registration.forms import UserSelfRegistrationForm
from sso.forms import bootstrap, mixins, BLANK_CHOICE_DASH, BaseForm

import logging
logger = logging.getLogger(__name__)


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), max_length=100, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_("E-mail address"), max_length=75, widget=bootstrap.TextInput())
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
        'unknown': _("That email address doesn't have an associated user account. Are you sure you've registered?"),
        'unusable': _("The user account associated with this email address cannot reset the password."),
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
                # check if the user was already imported from the streaming DB
                streaming_user_exists = UserAssociatedSystem.objects.filter(userid__iexact=email, application__uuid=settings.SSO_CUSTOM['STREAMING_UUID']).exists()
                if not streaming_user_exists:
                    # check if the user exist in the streaming db
                    from streaming.models import StreamingUser
                    try:
                        streaming_user = StreamingUser.objects.get_by_email(email)
                        self.password = streaming_user.password.decode("base64")
                        return email
                    except ObjectDoesNotExist:
                        pass
                    except Exception, e:
                        logger.exception(e)
                
            raise forms.ValidationError(self.error_messages['unknown'])
        else:
            for user in self.users_cache:
                if user.has_usable_password():
                    return email
        # no user with this email and a usable password found
        raise forms.ValidationError(self.error_messages['unusable'])
    
    def save(self, subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        from django.core.mail import send_mail
        email = self.cleaned_data["email"]
        current_site = get_current_site(request)
        site_name = settings.SSO_CUSTOM['SITE_NAME']
        domain = current_site.domain

        if (not self.password):
            # use parent method
            UserModel = get_user_model()
            active_users = UserModel._default_manager.filter(email__iexact=email, is_active=True)
            for user in active_users:
                # Make sure that no email is sent to a user that actually has
                # a password marked as unusable
                if not user.has_usable_password():
                    continue
                expiration_date = now() + datetime.timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS)
                c = {
                    'email': user.email,
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
                email = loader.render_to_string(email_template_name, c)
                send_mail(subject, email, from_email, [user.email])            
        else:
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


class UserAddForm(forms.ModelForm):
    """
    UserAddForm where no password is required
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
    email = forms.EmailField(label=_('E-mail'), required=True, widget=bootstrap.EmailInput())
    first_name = forms.CharField(label=_('First name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('first name'))}))
    last_name = forms.CharField(label=_('Last name'), required=True, widget=bootstrap.TextInput(attrs={'placeholder': capfirst(_('last name'))}))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email", 'notes')

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
        user = super(UserAddForm, self).save(commit=False)
        password = self.cleaned_data.get("password1", "")
        if password == "":
            password = get_random_string(40)
        user.set_password(password)
        
        user.username = default_username_generator(capfirst(self.cleaned_data.get('first_name')), capfirst(self.cleaned_data.get('last_name')))
        if commit:
            user.save()
        return user


class UserAddFormExt(UserAddForm):
    """
    UserAddForm with organisations, roles and notes element
    """
    organisation = forms.ModelChoiceField(queryset=None, cache_choices=True, required=False, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, cache_choices=True, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))
    role_profiles = forms.ModelMultipleChoiceField(queryset=None, cache_choices=True, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                                   help_text=_('Groups of application roles that are assigned together.'))
   
    def __init__(self, user, *args, **kwargs):
        super(UserAddFormExt, self).__init__(*args, **kwargs)
        self.fields['application_roles'].queryset = user.get_administrable_application_roles()
        self.fields['role_profiles'].queryset = user.get_administrable_role_profiles()
        self.fields['organisation'].queryset = user.get_administrable_organisations()
        if not user.has_perm("accounts.change_all_users"):
            self.fields['organisation'].required = True

    def save(self):
        user = super(UserAddFormExt, self).save()
        user.application_roles = self.cleaned_data["application_roles"]
        user.role_profiles = self.cleaned_data["role_profiles"]
        organisation = self.cleaned_data["organisation"]
        if organisation:
            user.organisations.add(organisation)
        return user
    

class AddressForm(BaseForm):
    class Meta:
        model = UserAddress
        fields = ('primary', 'address_type', 'addressee', 'street_address', 'city', 'postal_code', 'country', 'state') 
        widgets = {
                   'primary': bootstrap.CheckboxInput(),
                   'address_type': bootstrap.Select(),
                   'addressee': bootstrap.TextInput(attrs={'size': 50}),
                   'street_address': bootstrap.Textarea(attrs={'cols': 50, 'rows': 2}),
                   'city': bootstrap.TextInput(attrs={'size': 50}),
                   'postal_code': bootstrap.TextInput(attrs={'size': 50}),
                   'country': bootstrap.Select()
                   }
    
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
    
    def template(self):
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
    
    def opts(self):
        # i need the model verbose_name in the html form, is there a better way?
        return self._meta.model._meta
    
    def template(self):
        return 'edit_inline/tabular.html'


class UserSelfProfileForm(forms.Form):
    """
    Form for the user himself to change editable values
    """
    username = bootstrap.ReadOnlyField(label=_("Username"))
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('E-mail address'), widget=bootstrap.EmailInput())
    picture = forms.ImageField(label=_('Picture'), required=False, widget=bootstrap.ImageWidget())
    gender = forms.ChoiceField(label=_('Gender'), required=False, choices=(BLANK_CHOICE_DASH + User.GENDER_CHOICES), widget=bootstrap.Select())
    dob = forms.DateTimeField(label=_('Date of birth'), required=False, 
                widget=bootstrap.SelectDateWidget(years=range(datetime.datetime.now().year - 100, datetime.datetime.now().year + 1), required=False))
    homepage = forms.URLField(label=_('Homepage'), required=False, max_length=512, widget=bootstrap.TextInput())
    language = forms.ChoiceField(label=_("Language"), required=False, choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])), widget=bootstrap.Select())

    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        initial = kwargs.get('initial', {})
        object_data.update(initial)   
        kwargs['initial'] = object_data
        super(UserSelfProfileForm, self).__init__(*args, **kwargs)

        # if the user is already in at least 1 organisation, 
        # the organisation field is readonly
        # otherwise a required select field is displayed 
        organisation_field = None   
        if self.user.organisations.exists():
            organisation = u', '.join([x.__unicode__() for x in self.user.organisations.all()])
            organisation_field = bootstrap.ReadOnlyField(initial=organisation, label=_("Center"), help_text=_('Please use the contact form for a request to change this value.'))
        else:
            organisation_field = forms.ModelChoiceField(queryset=Organisation.objects.all().select_related('country'), cache_choices=True, label=_("Center"), widget=bootstrap.Select(), 
                                                        help_text=_('You can set this value only once.'), required=False)
        self.fields['organisation'] = organisation_field

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
        self.user.dob = cd.get('dob', None)
        self.user.gender = cd['gender']
        self.user.homepage = cd['homepage']
        self.user.language = cd['language']
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
    email = bootstrap.ReadOnlyField(label=_('E-mail address'))
    language = forms.ChoiceField(label=_("Language"), required=False, choices=(BLANK_CHOICE_DASH + sorted(list(settings.LANGUAGES), key=lambda x: x[1])), widget=bootstrap.Select())
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        object_data = model_to_dict(self.user)
        object_data['account_type'] = _('Center Account') if self.user.is_center else _('Member Account')
        initial = kwargs.get('initial', {})
        object_data.update(initial)
        kwargs['initial'] = object_data
        super(CenterSelfProfileForm, self).__init__(*args, **kwargs)

        if self.user.organisations.exists():
            organisation = u', '.join([x.__unicode__() for x in self.user.organisations.all()])
            organisation_field = bootstrap.ReadOnlyField(initial=organisation, label=_("Center"))
            self.fields['organisation'] = organisation_field

    def save(self):
        cd = self.cleaned_data
        self.user.language = cd['language']
        self.user.save()
        

class UserSelfProfileDeleteForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        super(UserSelfProfileDeleteForm, self).__init__(*args, **kwargs)
        
    def save(self):
        self.user.is_active = False
        self.user.save()
            
    
class BasicUserChangeForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = '__all__'

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


class UserSelfRegistrationForm2(UserSelfRegistrationForm):
    """
    Overwritten UserSelfRegistrationForm Form with additional  organisation field
    """
    UserSelfRegistrationForm.error_messages.update({
        'email_mismatch': _("The two email fields didn't match."),
    })
    organisation = forms.ModelChoiceField(queryset=Organisation.objects.all().select_related('country'), cache_choices=True, required=False, label=_("Center"), widget=bootstrap.Select())
    email2 = forms.EmailField(label=_('Repeat your Email'), required=True, widget=bootstrap.EmailInput())
    # for Bots. If you enter anything in this field you will be treated as a robot
    state = forms.CharField(label=_('State'), required=False, widget=bootstrap.HiddenInput())
    
    signer = signing.TimestampSigner()

    def __init__(self, data=None, *args, **kwargs):
        super(UserSelfRegistrationForm2, self).__init__(data, *args, **kwargs)
        
        if self.is_captcha_needed():
            self.fields['captcha'] = ReCaptchaField(label=_('Prove you are human'),
                                                    help_text=_('Please enter the words you see in the box, in order and separated by a space. Doing so helps prevent automated programs from abusing this service.'), 
                                                    error_messages={'captcha_invalid': _('Incorrect, please try again.')}, attrs={'theme': 'clean'})

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

    def clean_email2(self):
        email = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('email2')
        if email and email2:
            if email != email2:
                raise forms.ValidationError(
                    self.error_messages['email_mismatch'],
                    code='email_mismatch',
                )
        return email2
    
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
    Form for organisation and region admins
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email address already exists."),
    }
    username = forms.CharField(label=_("Username"), max_length=30, widget=bootstrap.TextInput())
    first_name = forms.CharField(label=_('First name'), max_length=30, widget=bootstrap.TextInput())
    last_name = forms.CharField(label=_('Last name'), max_length=30, widget=bootstrap.TextInput())
    email = forms.EmailField(label=_('E-mail address'), widget=bootstrap.EmailInput())
    is_active = forms.BooleanField(label=_('Active'), help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'), 
                                   widget=bootstrap.CheckboxInput(), required=False)
    is_center = forms.BooleanField(label=_('Center'), help_text=_('Designates that this user is representing a center and not a private person.'), 
                                   widget=bootstrap.CheckboxInput(), required=False)
    organisations = forms.ModelChoiceField(queryset=None, cache_choices=True, required=False, label=_("Organisation"), widget=bootstrap.Select())
    application_roles = forms.ModelMultipleChoiceField(queryset=None, cache_choices=True, required=False, widget=bootstrap.CheckboxSelectMultiple(), label=_("Application roles"))
    notes = forms.CharField(label=_("Notes"), required=False, max_length=1024, widget=bootstrap.Textarea(attrs={'cols': 40, 'rows': 10}))
    role_profiles = forms.ModelMultipleChoiceField(queryset=None, required=False, cache_choices=True, widget=bootstrap.CheckboxSelectMultiple(), label=_("Role profiles"),
                                                   help_text=_('Groups of application roles that are assigned together.'))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.user = kwargs.pop('instance')
        user_data = model_to_dict(self.user)
        try:
            # the user should have exactly 1 center 
            user_data['organisations'] = self.user.organisations.all()[0]
        except IndexError:
            # center is optional
            #logger.error("User without center?", exc_info=1)
            pass
        
        initial = kwargs.get('initial', {})
        initial.update(user_data)
        kwargs['initial'] = initial
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.fields['application_roles'].queryset = self.request.user.get_administrable_application_roles()
        self.fields['role_profiles'].queryset = self.request.user.get_administrable_role_profiles()
        self.fields['organisations'].queryset = self.request.user.get_administrable_organisations()

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            get_user_model().objects.exclude(pk=self.user.pk).get(username=username)
        except ObjectDoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])

    def clean_email(self):
        email = self.cleaned_data["email"]
        qs = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError(self.error_messages['duplicate_email'])
        return email
    
    def save(self):
        cd = self.cleaned_data
        current_user = self.request.user
        
        self.user.username = cd['username']
        self.user.email = cd['email']
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.is_active = cd['is_active']
        self.user.is_center = cd['is_center']
        self.user.notes = cd['notes']
        self.user.save()
        
        self.update_user_m2m_fields('application_roles', current_user)
        self.update_user_m2m_fields('role_profiles', current_user)
        self.update_user_m2m_fields('organisations', current_user)

        return self.user
