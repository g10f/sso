import logging
from jwt import InvalidTokenError
from django.conf import settings

from django.core import signing
from django.contrib.sessions.backends.signed_cookies import SessionStore as SignedCookiesSessionStore
from sso.oauth2.crypt import loads_jwt, make_jwt
from sso.sessions.backends import map_keys, inv_key_map, key_map

logger = logging.getLogger(__name__)


class SessionStore(SignedCookiesSessionStore):

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.
        """
        try:
            parsed = loads_jwt(self.session_key)
            parsed = map_keys(parsed, inv_key_map)
            if "_auth_user_backend" not in parsed:
                parsed["_auth_user_backend"] = "sso.auth.backends.EmailBackend"
            return parsed
        except (signing.BadSignature, ValueError, InvalidTokenError) as e:
            logger.exception("load error: %s", e)
            self.create()
        return {}

    def _get_session_key(self):
        """
        Most session backends don't need to override this method, but we do,
        because instead of generating a random string, we want to actually
        generate a secure url-safe Base64-encoded string of data as our
        session key.
        """
        session_cache = getattr(self, '_session_cache', {})
        session_cache = map_keys(session_cache, key_map)
        if "_auth_user_backend" in session_cache:
            del session_cache["_auth_user_backend"]
        session_cache["iss"] = settings.SSO_BASE_URL

        logger.debug("session_cache: %s", session_cache)
        return make_jwt(session_cache, max_age=settings.SESSION_COOKIE_AGE)
