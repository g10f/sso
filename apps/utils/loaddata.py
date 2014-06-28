# -*- coding: utf-8 -*-
import functools


import logging

logger = logging.getLogger(__name__)


def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """
    @functools.wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if 'raw' in kwargs:
            return
        signal_handler(*args, **kwargs)
    return wrapper
