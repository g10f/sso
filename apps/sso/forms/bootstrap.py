from django import forms
from django.contrib.gis import forms as gis_forms
from django.forms import widgets
from django.utils.html import format_html
from django.utils.translation import gettext as _


def add_class_to_css_class(classes, new_class):
    new_class = new_class.strip()
    if new_class:
        # Turn string into list of classes
        classes = classes.split(" ")
        # Strip whitespace
        classes = [c.strip() for c in classes]
        # Remove empty elements
        classes = list(filter(None, classes))
        # Test for existing
        if new_class not in classes:
            classes.append(new_class)
            # Convert to string
        classes = " ".join(classes)
    return classes


def add_class_to_attr(attrs, new_class):
    new_attrs = attrs.copy() if attrs else {}
    new_attrs['class'] = add_class_to_css_class(new_attrs.get('class', ''), new_class)
    return new_attrs


class Widget(forms.Widget):
    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-control')
        super().__init__(new_attrs, **kwargs)


class ReadOnlyWidget(forms.Widget):
    template_name = 'bootstrap/forms/widgets/read_only.html'

    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-control-plaintext')
        super().__init__(new_attrs, **kwargs)


class YesNoWidget(ReadOnlyWidget):
    template_name = 'bootstrap/forms/widgets/yes_no.html'


class ReadOnlyField(forms.Field):
    widget = ReadOnlyWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def bound_data(self, data, initial):
        # Always return initial because the widget doesn't
        # render an input field.
        return initial

    def has_changed(self, initial, data):
        return False


class ReadOnlyYesNoField(ReadOnlyField):
    widget = YesNoWidget


class ImageWidget(forms.ClearableFileInput):
    """
    An ImageField Widget a thumbnailed image as well as a link to the current one if it has one.
    """

    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-control')
        super().__init__(new_attrs, **kwargs)


class CheckboxSelectMultiple(forms.widgets.CheckboxSelectMultiple):
    template_name = 'bootstrap/forms/widgets/checkbox_select_multiple.html'


class HiddenInput(Widget, forms.HiddenInput):
    """
    Hidden field, can be used as honey pot for bots.
    The field is hidden with a css class and not with type="hidden"
    """
    pass


class TextInput(Widget, forms.TextInput):
    pass


class URLInput(Widget, forms.URLInput):
    pass


class EmailInput(Widget, forms.EmailInput):
    pass


class PasswordInput(Widget, forms.PasswordInput):
    pass


class Textarea(Widget, forms.Textarea):
    pass


class Select(forms.Select):
    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-select')
        super().__init__(new_attrs, **kwargs)


class Select2(forms.Select):
    class Media:
        css = {
            'all': ('css/select2-1.0.1.min.css', )
        }
        js = ('js/vendor/4.1.0-rc.0/select2.min.js', )

    def __init__(self, attrs=None, **kwargs):
        # add select2 class
        new_attrs = add_class_to_attr(attrs, 'select2 form-select w-100')
        super().__init__(new_attrs, **kwargs)


class SelectMultiple(forms.SelectMultiple):
    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-select')
        super().__init__(new_attrs, **kwargs)


class SelectMultipleWithCurrently(SelectMultiple):
    def __init__(self, attrs=None, currently=None):
        super().__init__(attrs)
        self.currently = currently

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        if self.currently is not None:
            html = format_html(
                '<p class="form-control-static">{} {}</p>{}',
                _('Currently:'), self.currently,
                html
            )
        return html


class CheckboxInput(forms.CheckboxInput):
    # overridden 'django/forms/widgets/checkbox.html' template
    # template_name = 'bootstrap/forms/widgets/checkbox.html'
    pass


class SelectDateWidget(widgets.SelectDateWidget):
    template_name = 'bootstrap/forms/widgets/select_date.html'

    def __init__(self, attrs=None, years=None, months=None, empty_label=None):
        a = attrs.copy() if attrs else {}
        # add bootstrap form-control css class
        css_classes = a.get('class', '').split()
        css_classes.append('form-select')
        a['class'] = ' '.join(css_classes)
        super().__init__(attrs=a, years=years, months=months, empty_label=empty_label)


class OSMWidget(gis_forms.OSMWidget):
    class Media:
        js = (
            'js/gis/OLMapWidgetExt-1.0.6.js',
        )


class FilteredSelectMultiple(forms.SelectMultiple):
    """
    A SelectMultiple with a JavaScript filter interface.

    Note that the resulting JavaScript assumes that the jsi18n
    catalog has been loaded in the page
    copy from django admin
    """

    @property
    def media(self):
        js = (
            'vendor/core.js',
            'vendor/SelectBox.js',
            'vendor/SelectFilter2.0.3.js',
            'formsets-1.3.js'
        )
        return forms.Media(js=["js/%s" % path for path in js])

    def __init__(self, verbose_name, attrs=None, choices=()):
        new_attrs = add_class_to_attr(attrs, 'selectfilter')
        new_attrs['data-field-name'] = verbose_name
        super().__init__(new_attrs, choices)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context
