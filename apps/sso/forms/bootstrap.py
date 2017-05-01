# -*- coding: utf-8 -*-
from sorl.thumbnail.shortcuts import get_thumbnail

from django import forms
from django.contrib.gis import forms as gis_forms
from django.forms import widgets
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


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
        classes = u" ".join(classes)
    return classes


def add_class_to_attr(attrs, new_class):
    new_attrs = attrs.copy() if attrs else {}
    new_attrs['class'] = add_class_to_css_class(new_attrs.get('class', ''), new_class)
    return new_attrs


class Widget(forms.Widget):
    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-control')
        super(Widget, self).__init__(new_attrs, **kwargs)


class ReadOnlyWidget(forms.Widget):
    template_name = 'bootstrap/forms/widgets/read_only.html'

    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        new_attrs = add_class_to_attr(attrs, 'form-control-static')
        super(ReadOnlyWidget, self).__init__(new_attrs, **kwargs)


class YesNoWidget(ReadOnlyWidget):
    template_name = 'bootstrap/forms/widgets/yes_no.html'


class ReadOnlyField(forms.Field):
    widget = ReadOnlyWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super(ReadOnlyField, self).__init__(*args, **kwargs)

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
    An ImageField Widget for django.contrib.admin that shows a thumbnailed
    image as well as a link to the current one if it has one.
    """
    template_with_initial = u'<div>%(clear_template)s<br />%(input_text)s: %(input)s</div>'
    template_with_clear = u'<div class="checkbox"><label>%(clear)s %(clear_checkbox_label)s </label></div>'

    def render(self, name, value, attrs=None):
        output = super(ImageWidget, self).render(name, value, attrs)
        if value and hasattr(value, 'url'):
            try:
                mini = get_thumbnail(value, '240x240', crop='center')
            except Exception:
                pass
            else:
                output = (
                             u'<div><a href="%s">'
                             u'<img class="img-thumbnail" src="%s" alt="%s"></a></div>%s'
                         ) % (value.url, mini.url, name, output)

        return mark_safe(output)


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


class Select(Widget, forms.Select):
    pass


class SelectMultiple(Widget, forms.SelectMultiple):
    pass


class SelectMultipleWithCurrently(SelectMultiple):
    def __init__(self, attrs=None, currently=None):
        super(SelectMultipleWithCurrently, self).__init__(attrs)
        self.currently = currently

    def render(self, name, value, attrs=None, choices=()):
        html = super(SelectMultipleWithCurrently, self).render(name, value, attrs)
        if self.currently is not None:
            html = format_html(
                u'<p class="form-control-static">{} {}</p>{}',
                _('Currently:'), self.currently,
                html
            )
        return html


class CheckboxInput(forms.CheckboxInput):
    template_name = 'bootstrap/forms/widgets/checkbox.html'


class SelectDateWidget(widgets.SelectDateWidget):
    template_name = 'bootstrap/forms/widgets/select_date.html'

    def __init__(self, attrs=None, years=None, months=None, empty_label=None):
        a = attrs.copy() if attrs else {}
        # add bootstrap form-control css class
        css_classes = a.get('class', '').split()
        css_classes.append('form-control')
        a['class'] = ' '.join(css_classes)
        super(SelectDateWidget, self).__init__(attrs=a, years=years, months=months, empty_label=empty_label)


class OSMWidget(gis_forms.OSMWidget):
    class Media:
        js = (
            'js/gis/OLMapWidgetExt-1.0.5.js',
        )

    def get_context(self, name, value, attrs):
        # TODO: Bug Django 1.11, BaseGeometryWidget.get_context don't call super(), so context don't have "widget" key
        context = super(OSMWidget, self).get_context(name, value, attrs)
        super_context = super(gis_forms.BaseGeometryWidget, self).get_context(name, value, attrs)
        super_context.update(context)
        return super_context
