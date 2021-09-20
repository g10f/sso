# mount this to apps/sso/settings/local_settings.py
# to configure the sso

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
#
# CACHES = {
#     'default': {
#         'BACKEND': 'sso.cache.backends.SSOCache',
#         'LOCATION': 'cache:11211',
#         'TIMEOUT': 300,
#         'KEY_PREFIX': 'sso'
#     }
# }
