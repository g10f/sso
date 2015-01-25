from django.utils import six
from django.utils.functional import lazy


def _string_format(string, dictionary):
    """
    Lazy variant of string formatting with %, needed for translations that are
    constructed from multiple parts.
    """
    return string % dictionary
string_format = lazy(_string_format, six.text_type)
