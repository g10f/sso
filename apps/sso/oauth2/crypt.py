import time
from jwt import decode, encode
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

MAX_AGE = 3600  # one hour


def make_jwt(payload, max_age=MAX_AGE):
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

    return encode(payload, key=settings.CERTS['default']['private_key'], algorithm='RS256')


def loads_jwt(jwt):
    """
    Reverse of make_jwt(), raises InvalidTokenError if something fails.
    """
    return decode(jwt, algorithms="RS256", key=settings.CERTS['default']['public_key'],
                  options={"verify_aud": False, "require_exp": True, "require_iat": True})
