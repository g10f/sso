# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from sso.forms.fields import EmailFieldLower
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from sso.emails.models import EmailForward, EmailAlias, GroupEmail, GroupEmailManager, Email, GROUP_EMAIL_TYPE


class EmailForwardForm(BaseForm):
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', 'email') 
        widgets = {
            'email': forms.HiddenInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super(EmailForwardForm, self).__init__(*args, **kwargs)


class EmailForwardInlineForm(BaseTabularInlineForm):
    """
    form without a primary field and with 
    a list of readonly primary emails
    """
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', ) 

    def template(self):
        return 'emails/email_forward_tabular.html'
    

class EmailForwardOnlyInlineForm(BaseTabularInlineForm):
    """
    form without a primary field
    """
    forward = EmailFieldLower(max_length=254, label=_('Email forwarding address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', ) 


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


class EmailManagerInlineForm(BaseTabularInlineForm):
    """
    inline form for the adminstrating the admins
    """
    manager_email = forms.CharField(max_length=254, label=_('Email'), widget=bootstrap.TextInput(attrs={'size': 50}))
    name = bootstrap.ReadOnlyField(label=_('Name'), initial='')

    class Meta:
        model = GroupEmailManager
        fields = ()

    def __init__(self, *args, **kwargs):
        super(EmailManagerInlineForm, self).__init__(*args, **kwargs)
        try:
            manager = self.instance.manager
            self.fields['manager_email'].initial = manager.primary_email()
            self.fields['name'].initial = u"%s %s" % (manager.first_name, manager.last_name)
        except ObjectDoesNotExist:
            pass

    def clean_manager_email(self):
        manager_email = self.cleaned_data['manager_email']
        if not get_user_model().objects.filter(useremail__email__iexact=manager_email).exists():
            msg = _('The user does not exists')
            raise ValidationError(msg)
            
        return manager_email

    def save(self, commit=True):
        if 'manager_email' in self.changed_data:
            manager_email = self.cleaned_data['manager_email']
            manager = get_user_model().objects.get(useremail__email__iexact=manager_email)
            self.instance.manager = manager

        instance = super(EmailManagerInlineForm, self).save(commit)
                
        return instance


class GroupEmailForm(BaseForm):
    email_value = EmailFieldLower(required=True, label=_("Email address"), widget=bootstrap.EmailInput())
    permission = forms.ChoiceField(label=_('Permission'), choices=Email.PERMISSION_CHOICES, widget=bootstrap.Select())
    is_active = forms.BooleanField(required=False, label=_("Active"), widget=bootstrap.CheckboxInput())
    
    class Meta:
        model = GroupEmail
        fields = ['homepage', 'name', 'is_guide_email']
        widgets = {
            'homepage': bootstrap.TextInput(attrs={'size': 50}),
            'name': bootstrap.TextInput(attrs={'size': 50}),
        }
        
    def __init__(self, *args, **kwargs):
        super(GroupEmailForm, self).__init__(*args, **kwargs)
        try:
            email = self.instance.email
            self.fields['is_active'].initial = email.is_active
            self.fields['email_value'].initial = str(email)
            self.fields['permission'].initial = email.permission
        except ObjectDoesNotExist:
            self.fields['is_active'].initial = True
        
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
        cd = self.changed_data
        if 'email_value' in cd or 'permission' in cd or 'is_active' in cd:
            created = False 
            try:
                email = self.instance.email
            except ObjectDoesNotExist:
                email = Email(email_type=GROUP_EMAIL_TYPE)
                created = True
            
            email.is_active = self.cleaned_data['is_active']
            email.email = self.cleaned_data['email_value']
            email.permission = self.cleaned_data['permission']
            email.save()
            if created:
                self.instance.email = email

        instance = super(GroupEmailForm, self).save(commit)
                
        return instance
