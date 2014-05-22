from django import forms 

BLANK_CHOICE_DASH = [("", "---------")]

class BaseForm(forms.ModelForm):
    """
    @property
    def media(self):
        media = super(BaseForm, self).media
        js = ['inlines.js']
        return forms.Media(js=[static('js/%s' % url) for url in js]) + media
    """
    def save(self, commit=True):
        if self.has_changed():
            return super(BaseForm, self).save(commit)
        else:
            return self.instance

"""
class ReadonlyField(object):
    def __init__(self, form, field, label=None):
        # Make self.field look a little bit like a field. This means that
        # {{ field.name }} must be a useful class name to identify the field.
        # For convenience, store other field-related data here too.
        if callable(field):
            class_name = field.__name__ if field.__name__ != '<lambda>' else ''
        else:
            class_name = field
        self.field = {
            'name': class_name,
            'label': label,
            'field': field,
            'help_text': help_text_for_field(class_name, form._meta.model)
        }
        self.form = form
        self.model_admin = model_admin
        self.is_first = is_first
        self.is_checkbox = False
        self.is_readonly = True

    def label_tag(self):
        attrs = {}
        if not self.is_first:
            attrs["class"] = "inline"
        label = self.field['label']
        return format_html('<label{0}>{1}:</label>',
                           flatatt(attrs),
                           capfirst(force_text(label)))

    def contents(self):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        field, obj, model_admin = self.field['field'], self.form.instance, self.model_admin
        try:
            f, attr, value = lookup_field(field, obj, model_admin)
        except (AttributeError, ValueError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                boolean = getattr(attr, "boolean", False)
                if boolean:
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_text(value)
                    if getattr(attr, "allow_tags", False):
                        result_repr = mark_safe(result_repr)
            else:
                if isinstance(f.rel, ManyToManyRel) and value is not None:
                    result_repr = ", ".join(map(six.text_type, value.all()))
                else:
                    result_repr = display_for_field(value, f)
        return conditional_escape(result_repr)
"""