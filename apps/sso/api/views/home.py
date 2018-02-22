
import logging

from django.urls import reverse
from django.views.decorators.cache import cache_page
from sso.api.response import JsonHttpResponse
from sso.utils.url import get_base_url

logger = logging.getLogger(__name__)

FIND_ASSOCIATION_EXPRESSION = "{?q,per_page,modified_since}"
FIND_USER_EXPRESSION = "{?q,per_page,app_id,modified_since,is_active,country_group_id,country,region_id,org_id,email}"
FIND_ORGANISATION_EXPRESSION = "{?q,per_page,modified_since,is_active,country_group_id,country,country_code," \
                               "region_id,latlng,dlt,with_unofficial,org_type,is_live}"
FIND_COUNTRY_EXPRESSION = "{?q,per_page,modified_since,country_group_id}"
FIND_REGION_EXPRESSION = "{?q,per_page,modified_since,country_group_id,country}"
FIND_COUNTRY_GROUP_EXPRESSION = "{?q,per_page,modified_since,country}"
FIND_USER_EMAILS_EXPRESSION = "{?q,app_id,modified_since,country_group_id,country,region_id,org_id,is_center}"


@cache_page(60 * 60)
def home(request):
    base_uri = get_base_url(request)
    resources = {
        "@id": "%s%s" % (base_uri, reverse('api:home')),
        "@type": "EntryPoint",
        "associations": "%s%s%s" % (base_uri, reverse('api:v2_associations'), FIND_ASSOCIATION_EXPRESSION),
        "association": "%s%s%s" % (base_uri, reverse('api:v2_associations'), "{association_id}/"),
        "country_groups": "%s%s%s" % (base_uri, reverse('api:v2_country_groups'), FIND_COUNTRY_GROUP_EXPRESSION),
        "country_group": "%s%s%s" % (base_uri, reverse('api:v2_country_groups'), "{country_group_id}/"),
        "countries": "%s%s%s" % (base_uri, reverse('api:v2_countries'), FIND_COUNTRY_EXPRESSION),
        "country": "%s%s%s" % (base_uri, reverse('api:v2_countries'), "{iso2_code}/"),
        "regions": "%s%s%s" % (base_uri, reverse('api:v2_regions'), FIND_REGION_EXPRESSION),
        "region": "%s%s%s" % (base_uri, reverse('api:v2_regions'), "{region_id}/"),
        "organisations": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), FIND_ORGANISATION_EXPRESSION),
        "organisation": "%s%s%s" % (base_uri, reverse('api:v2_organisations'), "{org_id}/"),
        "users": "%s%s%s" % (base_uri, reverse('api:v2_users'), FIND_USER_EXPRESSION),
        "user": "%s%s%s" % (base_uri, reverse('api:v2_users'), "{user_id}/"),
        "me": "%s%s" % (base_uri, reverse('api:v2_users_me')),
        "navigation_me": "%s%s" % (base_uri, reverse('api:v2_navigation_me')),
        "navigation": "%s%s" % (base_uri, reverse('api:v2_navigation_me').replace('/me/', '/{user_id}/', 1)),
        "picture_me": "%s%s" % (base_uri, reverse('api:v2_picture_me')),
        "picture": "%s%s" % (base_uri, reverse('api:v2_picture_me').replace('/me/', '/{user_id}/', 1)),
        "user_emails": "%s%s%s" % (base_uri, reverse('api:user_emails'), FIND_USER_EMAILS_EXPRESSION),
        # "emails": "%s%s" % (base_uri, reverse('api:emails', kwargs={'type': 'txt'}))
    }
    return JsonHttpResponse(data=resources, request=request)


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
        "primary": "http://g10f.de/primary",  # custom property
    }]
"""
