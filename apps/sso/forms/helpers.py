# -*- coding: utf-8 -*-
from django import forms
from django.utils.text import get_text_list
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_unicode
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

import logging
logger = logging.getLogger(__name__)


class ErrorList(forms.util.ErrorList):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        if form.is_bound:
            self.extend(form.errors.values())
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(errors_in_inline_form.values())


class ChangedDataList(list):
    """
    Stores all errors for the form/formsets in an add/change stage view.
    """
    def __init__(self, form, inline_formsets):
        if form.is_bound:
            self.extend(form.changed_data)
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
    from django.contrib.admin.models import LogEntry, CHANGE
    user_id = None
    if request.user.is_authenticated():
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
        object_repr=force_unicode(object),
        action_flag=CHANGE,
        change_message=message
    )
