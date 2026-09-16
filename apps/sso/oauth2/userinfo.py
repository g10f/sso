"""
Claims of the OpenID Connect userinfo endpoint
see https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims
"""
import calendar
from urllib.parse import urlsplit, urlunsplit

from .oidc_token import get_roles

OIDC_GENDER = {'m': 'male', 'f': 'female'}


def without_empty_values(claims):
    # claims without a value should be omitted instead of returning null or an empty string
    return {key: value for key, value in claims.items() if value not in (None, '')}


def absolute_uri(request, url):
    # request is an oauthlib request, so a missing scheme and host are taken from the request uri
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    request_uri = urlsplit(request.uri)
    return urlunsplit((scheme or request_uri.scheme, netloc or request_uri.netloc, path, query, fragment))


def get_address_claim(user):
    address = user.useraddress_set.order_by('-primary').select_related('country').first()
    if address is None:
        return None
    locality = ' '.join(filter(None, [address.postal_code, address.city]))
    formatted = '\n'.join(filter(None, [address.street_address, locality, address.region, address.country.printable_name]))
    return without_empty_values({
        'formatted': formatted,
        'street_address': address.street_address,
        'locality': address.city,
        'region': address.region,
        'postal_code': address.postal_code,
        'country': address.country.iso2_code,
    })


def get_userinfo_claims(request):
    """
    request is an oauthlib request, with user, client and scopes set by validate_bearer_token
    """
    user = request.user
    scopes = request.scopes
    claims = {'sub': user.uuid.hex}

    if 'profile' in scopes:
        claims.update({
            'name': user.get_full_name(),
            'given_name': user.first_name,
            'family_name': user.last_name,
            'preferred_username': user.username,
            'gender': OIDC_GENDER.get(user.gender),
            'birthdate': user.dob.isoformat() if user.dob else None,
            'website': user.homepage,
            'picture': absolute_uri(request, user.picture.url) if user.picture else None,
            'locale': user.language,
            'zoneinfo': user.timezone,
            'updated_at': int(calendar.timegm(user.get_last_modified_deep().utctimetuple())),
        })

    if 'email' in scopes:
        email = user.primary_email()
        if email is not None:
            claims['email'] = email.email
            claims['email_verified'] = email.confirmed

    if 'address' in scopes:
        claims['address'] = get_address_claim(user)

    if 'phone' in scopes:
        phone_number = user.userphonenumber_set.order_by('-primary').first()
        claims['phone_number'] = phone_number.phone if phone_number else None

    # same roles claim as in the id token
    if request.client.application:
        claims['roles'] = get_roles(user, request.client)

    return without_empty_values(claims)
