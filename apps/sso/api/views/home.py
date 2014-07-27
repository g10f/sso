# -*- coding: utf-8 -*-

from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse

from utils.url import base_url
from sso.api.response import JsonHttpResponse

import logging

logger = logging.getLogger(__name__)

FIND_USER_EXPRESSION = "{?q,org_id,per_page,app_id,modified_since}"
FIND_ORGANISATION_EXPRESSION = "{?q,per_page,country,modified_since}"


@cache_page(60 * 60)
def home(request):
    base_uri = base_url(request)
    resources = {
        "@id": "%s%s" % (base_uri, reverse('api:home')),
        "@type": "EntryPoint",
        "centers": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), FIND_ORGANISATION_EXPRESSION),
        "center": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), "{uuid}/"),
        "users": "%s%s%s" % (base_uri, reverse('api:v2_users'), FIND_USER_EXPRESSION),
        "user": "%s%s%s" % (base_uri, reverse('api:v2_users'), "{uuid}/"),
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

"""
@cache_page(60 * 60)
def home(request):
    base_uri = base_url(request)
    resources = {
        "resources": {
            "http://dwbn.org/specs/api/2.0/me": {
                "href": "%s%s" % (base_uri, reverse('api:v2_users_me')),
                "hints": {
                    "docs": "https://wiki.dwbn.org"
                }
            },
            "http://dwbn.org/specs/api/2.0/my-apps": {
                "href": "%s%s" % (base_uri, reverse('api:v2_navigation'))
            },
            "http://dwbn.org/specs/api/2.0/users": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v2_users'), FIND_USER_EXPRESSION),
                "href-vars": {
                    "q": "%s/param/q" % (base_uri),
                    "organisation__uuid": "%s/param/organisation__uuid" % (base_uri),
                    "per_page": "%s/param/per_page" % (base_uri),
                    "app_uuid": "%s/param/app_uuid" % (base_uri),
                    "modified_since": "%s/param/modified_since" % (base_uri)
                }
            },
            "http://dwbn.org/specs/api/2.0/organisations": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), FIND_ORGANISATION_EXPRESSION),
                "href-vars": {
                    "q": "%s/param/q" % (base_uri),
                    "per_page": "%s/param/per_page" % (base_uri),
                    "app_uuid": "%s/param/app_uuid" % (base_uri),
                    "modified_since": "%s/param/modified_since" % (base_uri)
                }
            },
            "http://dwbn.org/specs/api/2.0/user": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v2_users'), '{uuid}/'),
                "href-vars": {
                    "uuid": "%s/param/uuid" % (base_uri)
                }
            },
            "http://dwbn.org/specs/api/2.0/organisation": {
                "href-template": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), '{uuid}/'),
                "href-vars": {
                    "uuid": "%s/param/uuid" % (base_uri)
                }
            },
        }
    }
    return JsonHttpResponse(content=resources, request=request)
"""
