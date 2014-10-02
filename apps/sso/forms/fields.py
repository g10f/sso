# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from django.forms import fields
from sso.forms import bootstrap


class EmailFieldLower(fields.EmailField):
    widget = bootstrap.EmailInput(attrs={'size': 50})
    
    def to_python(self, value):
        return super(EmailFieldLower, self).to_python(value).lower()
    
    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        if 'label' not in kwargs:
            kwargs['label'] = _('email address')
        super(EmailFieldLower, self).__init__(max_length=max_length, min_length=min_length, *args, **kwargs)
