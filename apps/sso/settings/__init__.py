import logging

logger = logging.getLogger(__name__)

from .defaults import *
# Try loading local settings
try:
    from .local_settings import *
except ImportError as e:
    logger.info(e)
