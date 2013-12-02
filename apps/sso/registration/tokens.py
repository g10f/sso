from datetime import date
from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int
from django.utils.crypto import constant_time_compare, salted_hmac


class RegistrationTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the password
    reset mechanism.
    """
    def make_token(self, profile):
        """
        Returns a token that can be used once to do a password reset
        for the given profile.
        """
        return self._make_token_with_timestamp(profile, self._num_days(self._today()))

    def check_token(self, profile, token):
        """
        Check that a password reset token is correct for a given profile.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")  # @ReservedAssignment
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(profile, ts), token):
            return False

        # Check the timestamp is within limit
        if (self._num_days(self._today()) - ts) > settings.ACCOUNT_ACTIVATION_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, profile, timestamp):
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)

        # By hashing on the internal state of the profile and using state
        # that is sure to change (is_validated will change), we produce a hash that will be
        # invalid as soon as it is used.
        # We limit the hash to 20 chars to keep URL short
        key_salt = "registration.tokens.RegistrationTokenGenerator"

        # Ensure results are consistent across DB backends
        registered_timestamp = profile.date_registered.replace(microsecond=0, tzinfo=None)

        value = (unicode(profile.id) + unicode(profile.is_validated) +
                unicode(registered_timestamp) + unicode(timestamp))
        hash = salted_hmac(key_salt, value).hexdigest()[::2]  # @ReservedAssignment
        return "%s-%s" % (ts_b36, hash)

    def _num_days(self, dt):
        return (dt - date(2001, 1, 1)).days

    def _today(self):
        # Used for mocking in tests
        return date.today()

default_token_generator = RegistrationTokenGenerator()
