from django.template import loader
from django.utils import six
from django.utils.functional import lazy
from django.utils.translation import get_language, activate


def _string_format(string, dictionary):
    """
    Lazy variant of string formatting with %, needed for translations that are
    constructed from multiple parts.
    """
    return string % dictionary


string_format = lazy(_string_format, six.text_type)


def i18n_email_msg_and_subj(context, email_template_name, subject_template_name, language=None):
    def msg_and_subject():
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        msg = loader.render_to_string(email_template_name, context)
        return msg, subject

    if language:
        cur_language = get_language()
        try:
            activate(language)
            return msg_and_subject()
        finally:
            activate(cur_language)
    else:
        return msg_and_subject()
