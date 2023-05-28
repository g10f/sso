import datetime
from django.utils import timezone, dateparse


def parse_datetime_with_timezone_support(value):
    parsed = dateparse.parse_datetime(value)

    if not parsed:  # try date format
        parsed = dateparse.parse_date(value)
        if parsed is not None:
            parsed = datetime.datetime(parsed.year, parsed.month, parsed.day)

    # Confirm that dt is naive before overwriting its tzinfo.
    if parsed is not None and timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed

def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
