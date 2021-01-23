import logging

import time
from jwt import decode, encode, InvalidSignatureError, get_unverified_header

from django.conf import settings

logger = logging.getLogger(__name__)

MAX_AGE = 3600  # one hour


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

    signing = settings.SIGNING[algorithm]
    kid = signing['active']
    key = signing['keys'][kid]['SECRET_KEY']
    return encode(payload, key=key, algorithm=algorithm)  # , headers={"kid": kid})


def loads_jwt(jwt, algorithm="RS256", verify=True, options=None):
    _algorythm_keys = {'RS256': 'public_key', 'HS256': 'SECRET_KEY'}
    if options is None:
        options = {"verify_aud": False, "require": ["exp", "iat"], "verify_exp": True, "verify_iat": True}

    header = get_unverified_header(jwt)
    if 'kid' in header:
        key = settings.SIGNING[algorithm]['keys'][header['kid']][_algorythm_keys[algorithm]]
        return decode(jwt, algorithms=[algorithm], key=key, verify=verify, options=options)

    # else iterate over all keys
    for value in settings.SIGNING[algorithm]['keys'].values():
        try:
            key = value[_algorythm_keys[algorithm]]
            return decode(jwt, algorithms=[algorithm], key=key, verify=verify, options=options)
        except InvalidSignatureError as e:
            logger.debug(e)

    logger.info(f"InvalidSignatureError for {jwt}")
    raise InvalidSignatureError(jwt)
