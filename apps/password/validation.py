from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _, ungettext
from django.contrib.auth.password_validation import CommonPasswordValidator as DjangoCommonPasswordValidator
from django.contrib.auth.password_validation import MinimumLengthValidator as DjangoMinimumLengthValidator


# to get the text into the locale/django.po file for overwriting the translation
class MinimumLengthValidator(DjangoMinimumLengthValidator):
    def __init__(self, min_length=6):
        self.min_length = min_length

    def get_help_text(self):
        return ungettext(
            "Your password must contain at least %(min_length)d character.",
            "Your password must contain at least %(min_length)d characters.",
            self.min_length
        ) % {'min_length': self.min_length}


# to get the text into the locale/django.po file for overwriting the translation
class CommonPasswordValidator(DjangoCommonPasswordValidator):
    def get_help_text(self):
        return _("Your password can't be a commonly used password.")


class DigitsValidator(object):
    code = "min_digits"

    def __init__(self, min_digits=1):
        self.min_digits = min_digits

    def validate(self, password, user=None):
        if self.min_digits == 0:
            # nothing to validate
            return

        digits = set()
        for character in password:
            if character.isdigit():
                digits.add(character)

        if len(digits) < self.min_digits:
            raise ValidationError(
                _("Your password must contain %(min_digits)s or more digits") % {'min_digits': self.min_digits},
                code=self.code)

    def get_help_text(self):
        return ungettext(
            "Your password must contain at least %(min_digits)d digit.",
            "Your password must contain at least %(min_digits)d digits.",
            self.min_digits
        ) % {'min_digits': self.min_digits}
