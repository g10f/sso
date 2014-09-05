# -*- coding: utf-8 -*-

from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse

from utils.url import base_url
from sso.api.response import JsonHttpResponse

import logging

logger = logging.getLogger(__name__)

FIND_USER_EXPRESSION = "{?q,org_id,per_page,app_id,modified_since}"
FIND_ORGANISATION_EXPRESSION = "{?q,per_page,country,latlng,dlt,modified_since}"


@cache_page(60 * 60)
def home(request):
    base_uri = base_url(request)
    resources = {
        "@id": "%s%s" % (base_uri, reverse('api:home')),
        "@type": "EntryPoint",
        "organisations": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), FIND_ORGANISATION_EXPRESSION),
        "organisation": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), "{org_id}/"),
        "users": "%s%s%s" % (base_uri, reverse('api:v2_users'), FIND_USER_EXPRESSION),
        "user": "%s%s%s" % (base_uri, reverse('api:v2_users'), "{user_id}/"),
        "me": "%s%s" % (base_uri, reverse('api:v2_users_me')),
        "navigation": "%s%s" % (base_uri, reverse('api:v2_navigation'))
    }
    return JsonHttpResponse(content=resources, request=request)


"""
    object_context = ["http://www.w3.org/ns/hydra/context.jsonld", {
        "schema": "http://schema.org/",
        "name": "schema:name",
        "email": "schema:email",
        "founded": "schema:foundingDate",
        "homepage": "schema:url",
        "country": "schema:addressCountry",
        "last_modified": "schema:dateModified",
        "addresses": {
            "@id": "schema:PostalAddress", 
            "@container": "@index",
        },
        "street_address": "schema:streetAddress",        
        "city": "schema:addressLocality",        
        "postal_code": "schema:postalCode",        
        "region": "schema:addressRegion",
        "address_type": "schema:contactType",
        "primary": "http://dwbn.org/primary",  # custom property
    }]
"""
