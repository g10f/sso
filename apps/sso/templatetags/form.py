import logging

from django import template

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter
def selected_choice(form, field_name):
    key = form.data.get(field_name, None)
    if key is None:
        logger.warning(f'key for field "{field_name}" is None')
        return ''

    return next(map(lambda choice: choice[1], filter(lambda choice: str(choice[0]) == key, form.fields[field_name].choices)), '')
