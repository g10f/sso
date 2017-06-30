# -*- coding: utf-8 -*-
from django.contrib.auth.base_user import BaseUserManager
from django.forms import fields
from django.utils.translation import ugettext_lazy as _
from sso.forms import bootstrap


class EmailFieldLower(fields.EmailField):
    widget = bootstrap.EmailInput(attrs={'size': 50})

    def to_python(self, value):
        email = super(EmailFieldLower, self).to_python(value).rstrip().lstrip()
        return BaseUserManager.normalize_email(email)

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        if 'label' not in kwargs:
            kwargs['label'] = _('email address')
        super(EmailFieldLower, self).__init__(max_length=max_length, min_length=min_length, *args, **kwargs)
