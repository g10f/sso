from .defaults import *

# Try loading local settings
try:
    from .local_settings import *
except ImportError as e:
    print(f"Info: {e}")
