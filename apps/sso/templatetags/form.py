from django.template import Library

register = Library()

@register.filter
def selected_choice(form, field_name):
    key = form.data[field_name]
    if key:
        key = int(key)
    return dict(form.fields[field_name].choices)[key]


@register.filter
def by_pk(queryset, pk):
    # iterate because this uses prefetched queryset features
    # TODO: How can we check that the queryset is prefetched?
    for item in queryset:
        if str(item.pk) == pk:
            return item
    return None
