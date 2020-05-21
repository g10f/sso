import logging
import re
from base64 import b64decode
from mimetypes import guess_extension

import reversion

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.forms.models import inlineformset_factory
from django.forms.utils import ErrorList as DjangoErrorList
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text
from django.utils.text import get_text_list
from django.utils.translation import ugettext as _

logger = logging.getLogger(__name__)


def clean_base64_picture(base64_picture, max_upload_size=5242880):
    from django.template.defaultfilters import filesizeformat

    try:
        content_type, image_content = base64_picture.split(',', 1)
        content_type = re.findall(r'data:(\w+/\w+);base64', content_type)[0]

        if base64_picture and content_type:
            base_content_type = content_type.split('/')[0]
            if base_content_type in ['image']:
                # mimetypes.guess_extension return jpe which is quite uncommon for jpeg
                if content_type == 'image/jpeg':
                    file_ext = '.jpg'
                else:
                    file_ext = guess_extension(content_type)
                name = "%s%s" % (
                    get_random_string(7, allowed_chars='abcdefghijklmnopqrstuvwxyz0123456789'), file_ext)
                picture = ContentFile(b64decode(image_content), name=name)
                if picture.size > max_upload_size:
                    raise ValidationError(
                        _('Please keep filesize under %(filesize)s. Current filesize %(current_filesize)s') %
                        {'filesize': filesizeformat(max_upload_size),
                         'current_filesize': filesizeformat(picture.size)})

            else:
                raise ValidationError(_('File type is not supported'))
        return picture
    except Exception as e:
        raise ValidationError(force_text(e))


def get_optional_inline_formset(request, instance, parent_model, model, form, max_num=6, extra=1, queryset=None):
    InlineFormSet = inlineformset_factory(parent_model, model=model, form=form, extra=extra, max_num=max_num)
    if not instance:
        return None
    if request.method == 'POST':
        formset = InlineFormSet(request.POST, instance=instance, queryset=queryset)
        try:
            # Check if there was a InlineFormSet in the request because
            # InlineFormSet is only in the response when the organisation has an email
            formset.initial_form_count()
        except ValidationError:
            formset = None  # there is no InlineFormSet in the request
    else:
        formset = InlineFormSet(instance=instance, queryset=queryset)
    return formset


class ErrorList(DjangoErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """

    def __init__(self, form, inline_formsets):
        super().__init__()

        if form.is_bound:
            self.extend(form.errors.values())
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(errors_in_inline_form.values())


def get_media_errors_and_active_form(form, formsets=None):
    if formsets is None:
        formsets = {}
    media = form.media
    for fs in formsets:
        media = media + fs.media

    errors = ErrorList(form, formsets)
    active = ''
    if errors:
        if not form.is_valid():
            active = 'object'
        else:  # set the first formset with an error as active
            for formset in formsets:
                if not formset.is_valid():
                    active = formset.prefix
                    break
    return media, errors, active


class ChangedDataList(list):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """

    def __init__(self, form, inline_formsets=None):
        if form.is_bound:
            self.extend(form.changed_data)
            if inline_formsets is not None:
                for inline_formset in inline_formsets:
                    for inline_form in inline_formset.forms:
                        self.extend(inline_form.changed_data)

    def change_message(self):
        """
        Construct a change message from the changed object.
        """
        change_message = []
        if self:
            change_message.append(_('Changed %s.') % get_text_list(self, _('and')))
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')


def log_change(request, object, message):  # @ReservedAssignment
    """
    Log that an object has been successfully changed.

    The default implementation creates an admin LogEntry object.
    """
    # first use reversion API
    if reversion.is_active():
        reversion.set_comment(message)

    from django.contrib.admin.models import LogEntry, CHANGE
    if request.user.is_authenticated:
        user_id = request.user.pk
    else:
        try:
            user_id = get_user_model().objects.get(username__exact='Anonymous').pk
        except ObjectDoesNotExist:
            # we need a user id for logging
            return

    LogEntry.objects.log_action(
        user_id=user_id,  # request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_text(object),
        action_flag=CHANGE,
        change_message=message
    )
