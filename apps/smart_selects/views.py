import json
from functools import cmp_to_key

from django.apps import apps
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from smart_selects.utils import strcoll


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
    sorted(results, key=cmp_to_key(strcoll))
    result = []
    for item in results:
        result.append({'value': item.pk, 'display': str(item)})
    content = json.dumps(result)
    return HttpResponse(content, content_type='application/json')
