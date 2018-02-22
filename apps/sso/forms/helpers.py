from django.utils.text import get_text_list
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.encoding import force_text
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.utils import six
from django.forms.models import inlineformset_factory

import logging
logger = logging.getLogger(__name__)

try:
    from django.forms.utils import ErrorList as DjangoErrorList
except ImportError:  # django < 1.7 
    from django.forms.util import ErrorList as DjangoErrorList  # @UnusedImport
    

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
        super(ErrorList, self).__init__()

        if form.is_bound:
            self.extend(list(six.itervalues(form.errors)))
            for inline_formset in inline_formsets:
                self.extend(inline_formset.non_form_errors())
                for errors_in_inline_form in inline_formset.errors:
                    self.extend(list(six.itervalues(errors_in_inline_form)))


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
