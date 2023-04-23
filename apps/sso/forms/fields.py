from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.forms import fields
from django.forms.widgets import FILE_INPUT_CONTRADICTION
from django.utils.translation import gettext_lazy as _
from sso.forms import bootstrap
from sso.forms.helpers import clean_base64_picture


class EmailFieldLower(fields.EmailField):
    widget = bootstrap.EmailInput(attrs={'size': 50})

    def to_python(self, value):
        email = super().to_python(value).rstrip().lstrip()
        return BaseUserManager.normalize_email(email)

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        if 'label' not in kwargs:
            kwargs['label'] = _('email address')
        super().__init__(max_length=max_length, min_length=min_length, *args, **kwargs)


class Base64ImageField(fields.FileField):
    # Base class is FileField  to get the initial in django forms.py line 387
    # initial = self.get_initial_for_field(field, name)
    widget = bootstrap.ClearableBase64ImageWidget

    def clean(self, data, initial=None):
        # If the widget got contradictory inputs, we raise a validation error
        if data is FILE_INPUT_CONTRADICTION:
            raise ValidationError(self.error_messages['contradiction'], code='contradiction')
        # False means the field value should be cleared; further validation is
        # not needed.
        if data is False:
            if not self.required:
                return False
            # If the field is required, clearing is not possible (the widget
            # shouldn't return False data in that case anyway). False is not
            # in self.empty_value; if a False value makes it this far
            # it should be validated from here on out as None (so it will be
            # caught by the required check).
            data = None
        if not data and initial:
            return initial
        return super().clean(data)

    def to_python(self, data):
        if data in self.empty_values:
            return None

        if data:
            return clean_base64_picture(data)
        else:
            return data

    def has_changed(self, initial, data):
        return not self.disabled and data != ''

    def bound_data(self, data, initial):
        if data in (None, FILE_INPUT_CONTRADICTION):
            return initial
        return data
