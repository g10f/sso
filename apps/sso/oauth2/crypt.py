import logging

import time
from jwt import decode, encode

from django.conf import settings
from django.utils.encoding import force_str

logger = logging.getLogger(__name__)

MAX_AGE = 3600  # one hour

_algorithms = ["RS256", "HS256"]


def make_jwt(payload, max_age=MAX_AGE, algorithm="RS256"):
    """Make a signed JWT.
    See http://self-issued.info/docs/draft-jones-json-web-token.html.
    Args:
        payload: dict, Dictionary of data to convert to JSON and then sign.
    Returns:
        string, The JWT for the payload.
    """
    if "iat" not in payload:
        payload["iat"] = int(time.time())  # add  issued at time
    if "exp" not in payload:
        payload["exp"] = int(time.time()) + max_age  # add  expired at time

    if algorithm == "RS256":
        key = settings.CERTS['default']['PRIVATE_KEY']
    elif algorithm == "HS256":
        key = settings.SECRET_KEY
    else:
        raise NotImplementedError('Algorithm %s not supported', algorithm)
    bytes_string = encode(payload, key=key, algorithm=algorithm)
    return force_str(bytes_string)


def loads_jwt(jwt, algorithm="RS256", verify=True, options=None):
    """
    Reverse of make_jwt(), raises InvalidTokenError if something fails.
    """
    if algorithm == "RS256":
        key = settings.CERTS['default']['public_key']
    elif algorithm == "HS256":
        key = settings.SECRET_KEY
    else:
        raise NotImplementedError('Algorithm %s not supported', algorithm)
    if options is None:
        options = {"verify_aud": False, "require": ["exp", "iat"], "verify_exp": True, "verify_iat": True}

    return decode(jwt, algorithms=[algorithm], key=key, verify=verify, options=options)
