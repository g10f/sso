# -*- coding: utf-8 -*-
import re
import uuid

from django import forms
from django.core.validators import URLValidator
from django.db.models import CharField, URLField
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


class UUIDVersionError(Exception):
    pass


class UUIDField(CharField):
    """
    UUIDField for Django, supports all uuid versions which are natively
    supported by the uuid python module.
    """

    def __init__(self, verbose_name=None, name=None, auto=True, version=1, node=None, clock_seq=None, namespace=None, **kwargs):
        kwargs['max_length'] = 36
        self.auto = auto
        if auto:
            kwargs['blank'] = True
            kwargs['editable'] = kwargs.get('editable', False)
        self.version = version
        if version == 1:
            self.node, self.clock_seq = node, clock_seq
        elif version == 3 or version == 5:
            self.namespace, self.name = namespace, name
        super(UUIDField, self).__init__(verbose_name, name, **kwargs)

    def get_internal_type(self):
        return CharField.__name__  # @UndefinedVariable

    def create_uuid(self):
        if not self.version or self.version == 4:
            return uuid.uuid4()
        elif self.version == 1:
            return uuid.uuid1(self.node, self.clock_seq)
        elif self.version == 2:
            raise UUIDVersionError("UUID version 2 is not supported.")
        elif self.version == 3:
            return uuid.uuid3(self.namespace, self.name)
        elif self.version == 5:
            return uuid.uuid5(self.namespace, self.name)
        else:
            raise UUIDVersionError("UUID version %s is not valid." % self.version)

    def pre_save(self, model_instance, add):
        """
        if self.auto and add:
            value = self.create_uuid().hex
            setattr(model_instance, self.attname, value)
            return value
        else:
            value = super(UUIDField, self).pre_save(model_instance, add)
            if self.auto and not value:
                value = self.create_uuid().hex
                setattr(model_instance, self.attname, value)
        """
        value = super(UUIDField, self).pre_save(model_instance, add)
        if self.auto and not value:
            value = self.create_uuid().hex
            setattr(model_instance, self.attname, value)
        return value
