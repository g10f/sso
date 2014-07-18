# -*- coding: utf-8 -*-
from sso.emails.models import EmailForward, EmailAlias, Email
from sso.forms.fields import EmailFieldLower
from sso.forms import bootstrap, BaseForm, BaseTabularInlineForm
from django.utils.translation import ugettext_lazy as _


class EmailForwardForm(BaseTabularInlineForm):
    """
    - the primary email is readonly
    - without the primary field
    """
    forward = EmailFieldLower(max_length=254, label=_('Forward email address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', ) 

    def template(self):
        return 'emails/email_forward_tabular.html'
    

class AdminEmailForwardForm(BaseTabularInlineForm):
    forward = EmailFieldLower(max_length=254, label=_('Forward email address'))
    
    class Meta:
        model = EmailForward
        fields = ('forward', 'primary')
        widgets = {
            'primary': bootstrap.CheckboxInput()
        }

    
class EmailAliasForm(BaseTabularInlineForm):
    alias = EmailFieldLower(max_length=254, label=_('Alias email address'))
    
    class Meta:
        model = EmailAlias
        fields = ('alias', ) 


class EmailForm(BaseForm):    
    email = EmailFieldLower(max_length=254, label=_('Email address'))
    
    class Meta:
        model = Email
        fields = ['name', 'email', 'email_type', 'permission']
        widgets = {
            'name': bootstrap.TextInput(attrs={'size': 50}),
            'email_type': bootstrap.Select(),
            'permission': bootstrap.Select(),
        }
