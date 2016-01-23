import json
from django.apps import apps
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.utils import six

import locale
from smart_selects.utils import unicode_sorter


@cache_page(60)
def filterchain(request, app, model, field, value, manager=None):
    Model = apps.get_model(app, model)
    if value == '0':
        keywords = {str("%s__isnull" % field): True}
    else:
        keywords = {str(field): str(value)}
    if manager is not None and hasattr(Model, manager):
        queryset = getattr(Model, manager).all()
    else:
        queryset = Model.objects
    results = list(queryset.filter(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(six.text_type(x)))
    result = []
    for item in results:
        result.append({'value': item.pk, 'display': six.text_type(item)})
    content = json.dumps(result)
    return HttpResponse(content, content_type='application/json')


@cache_page(60)
def filterchain_all(request, app, model, field, value):
    Model = get_model(app, model)
    if value == '0':
        keywords = {str("%s__isnull" % field): True}
    else:
        keywords = {str(field): str(value)}
    results = list(Model.objects.filter(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(six.text_type(x)))
    final = []
    for item in results:
        final.append({'value': item.pk, 'display': six.text_type(item)})
    results = list(Model.objects.exclude(**keywords))
    results.sort(cmp=locale.strcoll, key=lambda x: unicode_sorter(six.text_type(x)))
    final.append({'value': "", 'display': "---------"})

    for item in results:
        final.append({'value': item.pk, 'display': six.text_type(item)})
    content = json.dumps(final)
    return HttpResponse(content, content_type='application/json')
