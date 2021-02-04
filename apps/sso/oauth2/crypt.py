import logging
import time

from jwt import decode, encode, InvalidSignatureError, get_unverified_header

from django.conf import settings
from sso.oauth2.keys import get_default_encoding_key_and_kid, get_decoding_key_by_kid

logger = logging.getLogger(__name__)


def make_jwt(payload, max_age=settings.SESSION_COOKIE_AGE, algorithm="RS256"):
    """
    Make a signed JWT.
    See http://self-issued.info/docs/draft-jones-json-web-token.html.
    Args:
        payload: dict, Dictionary of data to convert to JSON and then sign.
        max_age:
        algorithm:
    Returns:
        string, The JWT for the payload.
    """
    if "iat" not in payload:
        payload["iat"] = int(time.time())  # add  issued at time
    if "exp" not in payload:
        payload["exp"] = int(time.time()) + max_age  # add  expired at time

    key, kid = get_default_encoding_key_and_kid(algorithm)
    return encode(payload, key=key, algorithm=algorithm, headers={"kid": kid})


def loads_jwt(jwt, algorithm="RS256", options=None):
    _algorythm_keys = {'RS256': 'public_key', 'HS256': 'SECRET_KEY'}

    if options is None:
        options = {"verify_aud": False, "require": ["exp", "iat"], "verify_exp": True, "verify_iat": True}

    if options.get('verify_signature') is False:
        # when not verifing signature we dont need a key and algorithms
        return decode(jwt, options=options)

    header = get_unverified_header(jwt)
    if 'kid' not in header:
        logger.info(f"InvalidSignatureError for {jwt}")
        raise InvalidSignatureError(jwt)

    kid = header['kid']
    key = get_decoding_key_by_kid(kid, algorithm)
    return decode(jwt, algorithms=[algorithm], key=key, options=options)
