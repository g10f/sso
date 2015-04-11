from datetime import datetime

from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils import six


class EmailConfirmationTokenGenerator(object):
    """
    Strategy object used to generate and check tokens for the email confirmation mechanism.
    based on the django PasswordResetTokenGenerator
    """
    def make_token(self, user_email):
        """
        Returns a token that can be used once to do a password reset
        for the given user_email.
        """
        return self._make_token_with_timestamp(user_email, self._num_minutes(self._today()))

    def check_token(self, user_email, token):
        """
        Check that a email confirm token is correct for a given user_email.
        """
        # Parse the token
        try:
            ts_b36, hash = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_token_with_timestamp(user_email, ts), token):
            return False

        # Check the timestamp is within limit
        timeout = settings.SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES
        if (self._num_minutes(self._today()) - ts) > timeout:
            return False

        return True

    @staticmethod
    def _make_token_with_timestamp(user_email, timestamp):
        # timestamp is number of minutes since 2001-1-1.  Converted to
        # base 36, this gives us a 6 digit string until later then 3000
        ts_b36 = int_to_base36(timestamp)

        # By hashing on the internal state of the user_email we produce a hash that will be
        # invalid as soon as the email, user or confirmed flag changed.
        # We limit the hash to 20 chars to keep URL short
        key_salt = "sso.accounts.tokens.EmailConfirmationTokenGenerator"

        value = (six.text_type(user_email.user.pk) + user_email.email + six.text_type(user_email.confirmed) +
                 six.text_type(timestamp))
        hash = salted_hmac(key_salt, value).hexdigest()[::2]
        return "%s-%s" % (ts_b36, hash)

    @staticmethod
    def _num_minutes(dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds() / 60)

    @staticmethod
    def _today():
        # Used for mocking in tests
        return datetime.today()

email_confirm_token_generator = EmailConfirmationTokenGenerator()
