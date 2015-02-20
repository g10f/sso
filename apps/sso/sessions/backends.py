# -*- coding: utf-8 -*-

from django.core import signing
from django.contrib.sessions.backends.signed_cookies import SessionStore as SignedCookiesSessionStore
from sso.oauth2.crypt import loads_jwt, make_jwt


class SessionStore(SignedCookiesSessionStore):

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.
        """
        try:
            return loads_jwt(self.session_key)
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
        return make_jwt(session_cache)
