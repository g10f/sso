from django.template import Library

register = Library()

@register.filter
def selected_choice(form, field_name):
    key = form.data[field_name]
    if key:
        key = int(key)
    return dict(form.fields[field_name].choices)[key]
