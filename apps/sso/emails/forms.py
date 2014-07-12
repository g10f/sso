# -*- coding: utf-8 -*-
from sso.emails.models import EmailForward, EmailAlias
from sso.forms.fields import EmailFieldLower
from sso.forms import bootstrap, BaseTabularInlineForm
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
