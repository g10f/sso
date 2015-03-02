# -*- coding: utf-8 -*-
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
