# -*- coding: utf-8 -*-
import re

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.utils import prefix_validation_error
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.db.models import URLField
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from sso.utils.translation import string_format


@deconstructible
class URLValidatorEx(URLValidator):
    schemes = ['https']

    def __init__(self, domain, **kwargs):
        regex = re.compile(
            r'^(?:[a-z0-9.\-]*)://'  # scheme is validated separately
            + str(domain) +
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
        super(URLFormFieldEx, self).__init__(max_length=max_length, min_length=min_length, *args, **kwargs)


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


class SimpleArrayFieldEx(SimpleArrayField):
    default_error_messages = {
        'item_invalid': _('Item %(nth)s in the array did not validate: '),
        'items_occur_multiple': _('Some items occur muliple times.'),
    }

    def __init__(self, base_field, delimiter='\n', max_length=None, min_length=None, *args, **kwargs):
        super(SimpleArrayFieldEx, self).__init__(base_field, delimiter=delimiter, max_length=max_length,
                                                 min_length=min_length, *args, **kwargs)

    def validate(self, value):
        super(SimpleArrayField, self).validate(value)
        errors = []
        for index, item in enumerate(value):
            try:
                self.base_field.validate(item)
            except ValidationError as error:
                errors.append(prefix_validation_error(
                    error,
                    prefix=self.error_messages['item_invalid'],
                    code='item_invalid',
                    params={'nth': index + 1},
                ))
        if errors:
            raise ValidationError(errors)

    def run_validators(self, value):
        super(SimpleArrayField, self).run_validators(value)
        errors = []
        for index, item in enumerate(value):
            try:
                self.base_field.run_validators(item)
            except ValidationError as error:
                errors.append(prefix_validation_error(
                    error,
                    prefix=self.error_messages['item_invalid'],
                    code='item_invalid',
                    params={'nth': index + 1},
                ))
        if len(set(value)) < len(value):
            errors.append(self.error_messages['items_occur_multiple'])

        if errors:
            raise ValidationError(errors)


class URLArrayField(ArrayField):
    def __init__(self, size=None, **kwargs):
        super(URLArrayField, self).__init__(
            base_field=models.URLField(_('url'), validators=[validators.URLValidator(schemes=['http', 'https'])]),
            size=size, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(URLArrayField, self).deconstruct()
        kwargs.pop('base_field')
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            'form_class': SimpleArrayFieldEx,
            'base_field': self.base_field.formfield(),
            'max_length': self.size,
            'widget': forms.Textarea(attrs={'rows': '3'}),
        }
        defaults.update(kwargs)
        return super(ArrayField, self).formfield(**defaults)
