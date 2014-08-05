# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django import forms
from django.contrib.auth import get_user_model
from sso.emails.models import EmailForward, EmailAlias, GroupEmail, GroupEmailAdmin, Email, GROUP_EMAIL_TYPE
from sso.forms.fields import EmailFieldLower
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from django.utils.translation import ugettext_lazy as _


class EmailForwardForm(BaseForm):
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', 'email') 
        widgets = {
            'email': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        return super(EmailForwardForm, self).__init__(*args, **kwargs)


class EmailForwardInlineForm(BaseTabularInlineForm):
    """
    - the primary email is readonly
    - without the primary field
    """
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', ) 

    def template(self):
        return 'emails/email_forward_tabular.html'
    

class AdminEmailForwardInlineForm(BaseTabularInlineForm):
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', 'primary')
        widgets = {
            'primary': bootstrap.CheckboxInput()
        }

    
class EmailAliasInlineForm(BaseTabularInlineForm):
    alias = EmailFieldLower(max_length=254, label=_('Alias address'))
    
    class Meta:
        model = EmailAlias
        fields = ('alias', ) 


class EmailAdminInlineForm(BaseTabularInlineForm):
    """
    inline form for the adminstrating the admins
    """
    user_email = forms.CharField(max_length=254, label=_('Email'), widget=bootstrap.TextInput(attrs={'size': 50}))
    name = bootstrap.ReadOnlyField(label=_('Name'), initial='')
    
    class Meta:
        model = GroupEmailAdmin
        fields = ()

    def __init__(self, *args, **kwargs):
        super(EmailAdminInlineForm, self).__init__(*args, **kwargs)
        try:
            user = self.instance.user
            self.fields['user_email'].initial = user.email
            self.fields['name'].initial = u"%s %s" % (user.first_name, user.last_name)
        except ObjectDoesNotExist:
            pass

    def clean_user_email(self):
        user_email = self.cleaned_data['user_email']
        if not get_user_model().objects.filter(email=user_email).exists():
            msg = _('The user does not exists')
            raise ValidationError(msg)
            
        return user_email

    def save(self, commit=True):
        if 'user_email' in self.changed_data:
            user_email = self.cleaned_data['user_email']
            user = get_user_model().objects.get(email=user_email)
            self.instance.user = user

        instance = super(EmailAdminInlineForm, self).save(commit)
                
        return instance


class GroupEmailForm(BaseForm):    
    email_value = EmailFieldLower(required=True, label=_("Email address"), widget=bootstrap.EmailInput(attrs={'placeholder': 'name@diamondway-center.org'}))
    name = forms.CharField(max_length=254, label=_("Name"), widget=bootstrap.TextInput(attrs={'size': 50}))
    permission = forms.ChoiceField(label=_('Permission'), choices=Email.PERMISSION_CHOICES, widget=bootstrap.Select())
    
    class Meta:
        model = GroupEmail
        fields = ['homepage']
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
        }
        
    def __init__(self, *args, **kwargs):
        super(GroupEmailForm, self).__init__(*args, **kwargs)
        try:
            email = self.instance.email
            self.fields['email_value'].initial = str(email)
            self.fields['permission'].initial = email.permission
            self.fields['name'].initial = email.name
        except ObjectDoesNotExist:
            pass
        
    def clean_email_value(self):
        """
        the new email address must ..
        """
        email_value = self.cleaned_data['email_value']
        if Email.objects.filter(email__iexact=email_value).exclude(groupemail=self.instance).exists():
            msg = _('The email address already exists')
            raise ValidationError(msg)
            
        return email_value

    def save(self, commit=True):
        if 'email_value' in self.changed_data:
            created = False 
            try:
                email = self.instance.email
            except ObjectDoesNotExist:
                email = Email(email_type=GROUP_EMAIL_TYPE)
                created = True
            
            email.email = self.cleaned_data['email_value']
            email.name = self.cleaned_data['name']
            email.permission = self.cleaned_data['permission']
            email.save()
            if created:
                self.instance.email = email

        instance = super(GroupEmailForm, self).save(commit)
                
        return instance
