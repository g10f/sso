from .defaults import *


# Load the locl settings
try:
    from .local_settings import *
except ImportError as e:
    print("WARNING: Can not load local_settings files")
