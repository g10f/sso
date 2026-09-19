import json
from functools import cmp_to_key

from django.apps import apps
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_page
from smart_selects.utils import strcoll


# field is passed to queryset.filter(), so only the chained fields must be allowed
ALLOWED_CHAINS = {
    ('organisations', 'OrganisationCountry'): {'association'},
    ('organisations', 'AdminRegion'): {'organisation_country'},
}


@cache_page(60)
def filterchain(request, app, model, field, value, manager=None):
    if field not in ALLOWED_CHAINS.get((app, model), set()) or not str(value).isdigit():
        raise Http404
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
