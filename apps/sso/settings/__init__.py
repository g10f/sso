import logging

from .defaults import *

logger = logging.getLogger(__name__)

# Try loading local settings
try:
    from .local_settings import *
except ImportError as e:
    logger.info(e)
