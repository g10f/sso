# -*- coding: utf-8 -*-
import re

from django import forms
from django.core.validators import URLValidator
from django.db.models import URLField
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from utils.translation import string_format


@deconstructible
class URLValidatorEx(URLValidator):
    schemes = ['https']

    def __init__(self, domain, **kwargs):
        regex = re.compile(
            r'^(?:[a-z0-9\.\-]*)://'  # scheme is validated separately
            + domain +
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if kwargs is None:
            kwargs = {}
        kwargs['regex'] = regex
        super(URLValidatorEx, self).__init__(**kwargs)


class URLFormFieldEx(forms.URLField):

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        domain = kwargs.pop('domain')
        validators = [URLValidatorEx(domain)]
        error_messages = {
            'invalid': string_format(_('Enter a valid URL starting with https://%(domain)s'), {'domain': domain}),
        }
        kwargs['error_messages'] = error_messages
        kwargs['validators'] = validators
        super(URLFormFieldEx, self).__init__(max_length=None, min_length=None, *args, **kwargs)


class URLFieldEx(URLField):

    def __init__(self, domain, verbose_name=None, name=None, **kwargs):
        self.domain = domain
        self.default_validators = [URLValidatorEx(domain)]
        super(URLFieldEx, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(URLFieldEx, self).deconstruct()
        kwargs['domain'] = self.domain
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            'form_class': URLFormFieldEx,
            'domain': self.domain
        }
        defaults.update(kwargs)
        return super(URLFieldEx, self).formfield(**defaults)
