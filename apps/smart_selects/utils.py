import locale

import six


def strcoll(a, b):
    return locale.strcoll(six.text_type(a), six.text_type(b))
