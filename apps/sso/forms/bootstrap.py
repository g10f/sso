# -*- coding: utf-8 -*-
from django import forms 
from django.utils.safestring import mark_safe
from sorl.thumbnail.shortcuts import get_thumbnail
#from django.forms.util import flatatt
from django.utils.encoding import force_text
from django.utils.html import format_html


class Widget(forms.Widget):
    def __init__(self, attrs=None):
        # add form-control class
        if attrs == None:
            attrs = {}    
        css_classes = attrs.get('class', '').split()
        css_classes.append('form-control')
        attrs['class'] = ' '.join(css_classes)
        super(Widget, self).__init__(attrs)
    
    def add_required(self):
        if self.is_required:
            if self.attrs is None:
                self.attrs = {}
            self.attrs['required'] = ''
        
    
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
        if not new_class in classes:
            classes.append(new_class)
            # Convert to string
        classes = u" ".join(classes)
    return classes


class StaticInput(forms.TextInput):
    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        
        attrs['type'] = 'hidden'
        klass = add_to_css_class(self.attrs.pop('class', ''), 'form-control-static')
        klass = add_to_css_class(klass, attrs.pop('class', ''))
        base = super(StaticInput, self).render(name, value, attrs)
        return mark_safe(base + u'<p class="%s">%s</p>' % (klass, value))


class ImageWidget(forms.ClearableFileInput):
    """
    An ImageField Widget for django.contrib.admin that shows a thumbnailed
    image as well as a link to the current one if it hase one.
    """

    template_with_initial = u'%(clear_template)s<br />%(input_text)s: %(input)s'
    template_with_clear = u'<div class="checkbox"><label>%(clear)s %(clear_checkbox_label)s </label></div>'
    #template_with_clear = u'<label for="%(clear_checkbox_id)s"></label><div class="checkbox">%(clear_checkbox_label)s %(clear)s'

    def render(self, name, value, attrs=None):
        output = super(ImageWidget, self).render(name, value, attrs)
        if value and hasattr(value, 'url'):
            try:
                mini = get_thumbnail(value, 'x108', upscale=False)
            except Exception:
                pass
            else:
                output = (
                    u'<div><a href="%s">'
                    u'<img src="%s" alt=""></a></div>%s'  # TODO: add alt text
                    ) % (value.url, mini.url, output)
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


class HiddenInput(Widget, forms.TextInput):
    """
    Hidden field, can be used as honey pot for bots. 
    The field is hidden with a css class and not with type="hidden" 
    """
    is_hidden = True
        

class TextInput(Widget, forms.TextInput):
    
    def render(self, name, value, attrs=None):
        self.add_required()
        return super(TextInput, self).render(name, value, attrs)

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
