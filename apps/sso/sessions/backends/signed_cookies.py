# -*- coding: utf-8 -*-
from django.conf import settings

from django.core import signing
from django.contrib.sessions.backends.signed_cookies import SessionStore as SignedCookiesSessionStore


class SessionStore(SignedCookiesSessionStore):
    salt = "signed_cookies"

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.
        """
        try:
            return signing.loads(self.session_key,
                serializer=self.serializer,
                # This doesn't handle non-default expiry dates, see #19201
                max_age=settings.SESSION_COOKIE_AGE,
                salt=self.salt)
        except (signing.BadSignature, ValueError):
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
        return signing.dumps(session_cache, compress=True,
            salt=self.salt,
            serializer=self.serializer)

