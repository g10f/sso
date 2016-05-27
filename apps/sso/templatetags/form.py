from django.template import Library

register = Library()


@register.filter
def selected_choice(form, field_name):
    key = form.data.get(field_name, None)
    if key is not None:
        try:
            return dict(form.fields[field_name].choices)[key]
        except KeyError:
            # key is int in model choices
            return dict(form.fields[field_name].choices)[int(key)]
    else:
        return ''


@register.filter
def by_key(dictionary, key):
    return dictionary.get(key, None)
