from .defaults import *

# Load the local settings
try:
    from .local_settings import *
except ImportError as e:
    print("WARNING: Can not load local_settings files")

# overwrite the secrets in your local_settings.py
SECRET_KEY = SIGNING['HS256']['keys'][SIGNING['HS256']['active']]['SECRET_KEY']
