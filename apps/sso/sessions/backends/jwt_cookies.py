import logging
from jwt import InvalidTokenError
from django.conf import settings

from django.core import signing
from django.contrib.sessions.backends.signed_cookies import SessionStore as SignedCookiesSessionStore
from sso.oauth2.crypt import loads_jwt, make_jwt


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
        logger.debug("session_cache: %s", session_cache)
        return make_jwt(session_cache, max_age=settings.SESSION_COOKIE_AGE)
