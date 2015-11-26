# -*- coding: utf-8 -*-
import datetime
import re

from django import forms 
from django.utils import datetime_safe
from django.utils.dates import MONTHS
from django.utils.formats import get_format
from django.utils.safestring import mark_safe
from django.conf import settings

from sorl.thumbnail.shortcuts import get_thumbnail
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils import six


class Widget(forms.Widget):
    def __init__(self, attrs=None, **kwargs):
        # add form-control class
        if attrs is None:
            attrs = {}    
        css_classes = attrs.get('class', '').split()
        css_classes.append('form-control')
        attrs['class'] = ' '.join(css_classes)
        super(Widget, self).__init__(attrs, **kwargs)

    def add_required(self):
        pass
        # does not work with inline formsets
        """
        if self.is_required:
            if self.attrs is None:
                self.attrs = {}
            self.attrs['required'] = ''
        """

    
def add_to_css_class(classes, new_class):
    new_class = new_class.strip()
    if new_class:
        # Turn string into list of classes
        classes = classes.split(" ")
        # Strip whitespace
        classes = [c.strip() for c in classes]
        # Remove empty elements
        classes = filter(None, classes)
        # Test for existing
        if new_class not in classes:
            classes.append(new_class)
            # Convert to string
        classes = u" ".join(classes)
    return classes

"""
class StaticInput(forms.TextInput):
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        
        attrs['type'] = 'hidden'
        
        klass = add_to_css_class(self.attrs.pop('class', ''), 'form-control-static')
        klass = add_to_css_class(klass, attrs.pop('class', ''))

        base = super(StaticInput, self).render(name, value, attrs)
        return mark_safe(base + u'<p class="%s">%s</p>' % (klass, value))
"""

class ReadOnlyWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
                
        klass = add_to_css_class(self.attrs.pop('class', ''), 'form-control-static')
        klass = add_to_css_class(klass, attrs.pop('class', ''))
        return mark_safe(u'<p class="%s">%s</p>' % (klass, value if value is not None else ''))


class YesNoWidget(ReadOnlyWidget):
    def render(self, name, value, attrs=None):
        if value:
            value = '<span class="glyphicon glyphicon-ok-sign"></span>'
        else:
            value = '<span class="glyphicon glyphicon-minus-sign"></span>'
        return super(YesNoWidget, self).render(name, value, attrs)
            
    
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


class CheckboxFieldRenderer(forms.widgets.ChoiceFieldRenderer):
    choice_input_class = forms.widgets.CheckboxChoiceInput
    
    def render(self):
        """
        Outputs a list of <div> for this set of choice fields.
        If an id was given to the field, it is applied to the enclosing <div> (each
        item in the list will get an id of `$id_$i`).
        """
        id_ = self.attrs.get('id', None)
        start_tag = format_html('<div id="{0}">', id_) if id_ else '<div>'
        output = [start_tag]
        for widget in self:
            output.append(format_html('<div class="checkbox">{0}</div>', force_text(widget)))
        output.append('</div>')
        return mark_safe('\n'.join(output))
    
    
class CheckboxSelectMultiple(forms.widgets.CheckboxSelectMultiple):
    renderer = CheckboxFieldRenderer


class HiddenInput(Widget, forms.HiddenInput):
    """
    Hidden field, can be used as honey pot for bots. 
    The field is hidden with a css class and not with type="hidden" 
    """
    pass


class TextInput(Widget, forms.TextInput):
    
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(TextInput, self).render(name, value, attrs)


class URLInput(Widget, forms.URLInput):

    def render(self, name, value, attrs=None):
        self.add_required()
        return super(URLInput, self).render(name, value, attrs)


class EmailInput(Widget, forms.EmailInput):
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(EmailInput, self).render(name, value, attrs)


class PasswordInput(Widget, forms.PasswordInput):
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(PasswordInput, self).render(name, value, attrs)


class Textarea(Widget, forms.Textarea):
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(Textarea, self).render(name, value, attrs)


class Select(Widget, forms.Select):
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(Select, self).render(name, value, attrs)


class SelectMultiple(Widget, forms.SelectMultiple):
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(SelectMultiple, self).render(name, value, attrs)


class CheckboxInput(forms.CheckboxInput):

    def render(self, name, value, attrs=None):
        return format_html('<div class="checkbox">{0}</div>', super(CheckboxInput, self).render(name, value, attrs))
    

def _parse_date_fmt():
    fmt = get_format('DATE_FORMAT')
    escaped = False
    output = []
    for char in fmt:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char in 'Yy':
            output.append('year')
            # if not self.first_select: self.first_select = 'year'
        elif char in 'bEFMmNn':
            output.append('month')
            # if not self.first_select: self.first_select = 'month'
        elif char in 'dj':
            output.append('day')
            # if not self.first_select: self.first_select = 'day'
    return output


class SelectDateWidget(Widget):
    """
    A Widget that splits date input into three <select> boxes.

    This also serves as an example of a Widget that has more than one HTML
    element and hence implements value_from_datadict.
    """
    none_value = (0, '---')
    month_field = '%s_month'
    day_field = '%s_day'
    year_field = '%s_year'

    def __init__(self, attrs=None, years=None, required=True):
        # years is an optional list/tuple of years to use in the "year" select box.
        self.attrs = attrs or {}
        self.required = required
        if years:
            self.years = years
        else:
            this_year = datetime.date.today().year
            self.years = range(this_year, this_year + 10)

    def render(self, name, value, attrs=None):
        RE_DATE = re.compile(r'(\d{4})-(\d\d?)-(\d\d?)$')
        try:
            year_val, month_val, day_val = value.year, value.month, value.day
        except AttributeError:
            year_val = month_val = day_val = None
            if isinstance(value, six.string_types):
                if settings.USE_L10N:
                    try:
                        input_format = get_format('DATE_INPUT_FORMATS')[0]
                        v = datetime.datetime.strptime(value, input_format)
                        year_val, month_val, day_val = v.year, v.month, v.day
                    except ValueError:
                        pass
                else:
                    match = RE_DATE.match(value)
                    if match:
                        year_val, month_val, day_val = [int(v) for v in match.groups()]
        choices = [(i, i) for i in self.years]
        year_html = self.create_select(name, self.year_field, value, year_val, choices)
        choices = MONTHS.items()
        month_html = self.create_select(name, self.month_field, value, month_val, choices)
        choices = [(i, i) for i in range(1, 32)]
        day_html = self.create_select(name, self.day_field, value, day_val, choices)

        output = ['<div class="row">']
        for field in _parse_date_fmt():
            if field == 'year':
                output.append('<div class="col-xs-4">')
                output.append(year_html)
                output.append('</div>')
            elif field == 'month':
                output.append('<div class="col-xs-5">')
                output.append(month_html)
                output.append('</div>')
            elif field == 'day':
                output.append('<div class="col-xs-3">')
                output.append(day_html)
                output.append('</div>')
        output.append('</div>')
        return mark_safe(u'\n'.join(output))

    def id_for_label(cls, id_):
        first_select = None
        field_list = _parse_date_fmt()
        if field_list:
            first_select = field_list[0]
        if first_select is not None:
            return '%s_%s' % (id_, first_select)
        else:
            return '%s_month' % id_
    id_for_label = classmethod(id_for_label)

    def value_from_datadict(self, data, files, name):
        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        d = data.get(self.day_field % name)
        if y == m == d == "0":
            return None
        if y and m and d:
            if settings.USE_L10N:
                input_format = get_format('DATE_INPUT_FORMATS')[0]
                try:
                    date_value = datetime.date(int(y), int(m), int(d))
                except ValueError:
                    return '%s-%s-%s' % (y, m, d)
                else:
                    date_value = datetime_safe.new_date(date_value)
                    return date_value.strftime(input_format)
            else:
                return '%s-%s-%s' % (y, m, d)
        return data.get(name, None)

    def create_select(self, name, field, value, val, choices):
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name
        if not (self.required and val):
            choices.insert(0, self.none_value)
        local_attrs = self.build_attrs(id=field % id_)
        s = Select(choices=choices)
        select_html = s.render(field % name, val, local_attrs)
        return select_html

    """
    def _has_changed(self, initial, data):
        input_format = get_format('DATE_INPUT_FORMATS')[0]
        if data:
            data = datetime_safe.datetime.strptime(data, input_format).date()
        return super(SelectDateWidget, self)._has_changed(initial, data)
    """

from django.contrib.gis.forms.widgets import BaseGeometryWidget
from django.contrib.gis import gdal
class OSMWidget(BaseGeometryWidget):
    """
    An OpenLayers/OpenStreetMap-based widget.
    """
    template_name = 'gis/openlayers-osm.html'
    default_lon = 5
    default_lat = 47

    class Media:
        js = (
            #'//cdnjs.cloudflare.com/ajax/libs/openlayers/2.13.1/OpenLayers.js',
            'js/openlayer/2.13.1/OpenLayers.js',
            'js/gis/OpenStreetMap.js',
            'js/gis/OLMapWidget-1.0.3.js',
        )

    @property
    def map_srid(self):
        # Use the official spherical mercator projection SRID on versions
        # of GDAL that support it; otherwise, fallback to 900913.
        if gdal.HAS_GDAL and gdal.GDAL_VERSION >= (1, 7):
            return 3857
        else:
            return 900913

    def render(self, name, value, attrs=None):
        default_attrs = {
            'default_lon': self.default_lon,
            'default_lat': self.default_lat,
        }
        if attrs:
            default_attrs.update(attrs)
        return super(OSMWidget, self).render(name, value, default_attrs)
