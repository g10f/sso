# -*- coding: utf-8 -*-
# Django settings for sso project.
import os
import sys
import socket

try:
    RUNNING_DEVSERVER = (sys.argv[1] == 'runserver')
except:
    RUNNING_DEVSERVER = False

if RUNNING_DEVSERVER:
    INTERNAL_IPS = ('127.0.0.1',)
    DEBUG = True
    LOCAL_DEV = True
else:
    DEBUG = False
    LOCAL_DEV = False

TEMPLATE_DEBUG = DEBUG

SSO_CUSTOM = {
    'BRAND': 'G10F',
    'SITE_NAME': 'G10F',
    'ABOUT': 'http://g10f.de/',
    'APP_UUID': 'fa467234b81e4838a009e38d9e655d18',
    'STREAMING_UUID': 'c362bea58c67457fa32234e3178285c4',
    'STYLESHEET': 'css/default-1.0.7.css',
    'SYLE_LESS': 'less/default.less',
    'FAVICON': 'ico/favicon.ico'
}

EMAIL_SUBJECT_PREFIX = '[SSO] '

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # django 1.7 settings

hostname = socket.gethostname().upper()
TEST = 'test' in sys.argv

ADMINS = (
    ('Gunnar Scherf', 'webmaster@g10f.de'),
)
MANAGERS = ADMINS
USER_CHANGE_EMAIL_RECIPIENT_LIST = ['webmaster@g10f.de']
DEFAULT_FROM_EMAIL = 'webmaster@g10f.de'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # 'django.db.backends.postgresql_psycopg2',
        'NAME': 'sso',
        'USER': 'sso',
        'PASSWORD': 'sso',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 60
    },
}

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'

ABSOLUTE_URL_OVERRIDES = {
    'accounts.user': lambda u: "/api/v1/users/%s/" % u.uuid,
}

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, '../../static/htdocs/sso/static')
MEDIA_ROOT = os.path.join(BASE_DIR, '../../static/htdocs/sso/media')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'sso/static'),
)

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

if DEBUG:
    # don't use cached loader
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.eggs.Loader',
    )
else:
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.eggs.Loader',
        )),
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'sso.oauth2.middleware.OAuthAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'current_user.middleware.CurrentUserMiddleware',
    'sso.middleware.CookieProlongationMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "sso.context_processors.settings"
)

ROOT_URLCONF = 'sso.urls'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'sso/templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.formtools',
    'django.contrib.admin',
    'django.contrib.gis',
    'sorl.thumbnail',
    'captcha',
    'passwords',
    'l10n',
    'smart_selects',
    'sso',
    'sso.emails',
    'sso.organisations',
    'sso.accounts',
    'sso.registration',
    'sso.auth',
    'sso.oauth2',
)

THUMBNAIL_QUALITY = 100

L10N_SETTINGS = {
    'currency_formats': {
        'USD': {'symbol': u'$', 'positive': u"$%(val)0.2f", 'negative': u"-$%(val)0.2f", 'decimal': '.'},
        'GBP': {'symbol': u'£', 'positive': u"£%(val)0.2f", 'negative': u"-£%(val)0.2f", 'decimal': '.'},
        'EURO': {'symbol': u'€', 'positive': u"%(val)0.2f €", 'negative': u"-%(val)0.2f €", 'decimal': ','},
    },
    'default_currency': 'EURO',
}

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'sso/locale'),
)

AUTHENTICATION_BACKENDS = (
    'sso.auth.backends.EmailBackend',
    'sso.oauth2.backends.OAuth2Backend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'sso.auth.hashers.MoinSha1PasswordHasher',
    'sso.auth.hashers.OsCommerceMD5PasswordHasher',
)
POSTGIS_VERSION = (2, 0, 3)

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
AUTH_USER_MODEL = 'accounts.User'

REGISTRATION = {
    'OPEN': False,
    'TOKEN_EXPIRATION_DAYS': 7,
    'ACTIVATION_EXPIRATION_DAYS': 60,
}
RECAPTCHA_PUBLIC_KEY = '6LccjewSAAAAAPcFZmUtuzRVkU6hhOona0orqgKh'
RECAPTCHA_PRIVATE_KEY = '6LccjewSAAAAAAhJzHuEyVV40AYApL6CpmjqlmX8'
RECAPTCHA_USE_SSL = True

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 60 * 20  # seconds * Minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
# SESSION_ENGINE = 'sso.sessions.backends'
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies' 
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = None 
CSRF_FAILURE_VIEW = 'sso.views.csrf.csrf_failure'

if not(LOCAL_DEV or TEST):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

PASSWORD_COMPLEXITY = {  # You can ommit any or all of these for no limit for that particular set
    "UPPER": 0,       # Uppercase
    "LOWER": 0,       # Lowercase
    "DIGITS": 1,      # Digits
    "PUNCTUATION": 0,  # Punctuation (string.punctuation)
    "NON ASCII": 0,   # Non Ascii (ord() >= 128)
    "WORDS": 0        # Words (substrings seperates by a whitespace)
}

# Configure logging
if DEBUG:
    LOGGING_LEVEL = 'DEBUG'
else:
    LOGGING_LEVEL = 'INFO'

LOGGING_HANDLERS = ['mail_admins', 'error', ]
if DEBUG:
    LOGGING_HANDLERS += ['debug', 'console']

ERROR_LOGFILE = "../../logs/sso-django-error.log"
INFO_LOGFILE = "../../logs/sso-django-info.log"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
        'error': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, ERROR_LOGFILE),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, INFO_LOGFILE),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'error', ],
            'level': 'WARNING',
            'propagate': True,
        },
        'sso': {
            'handlers': LOGGING_HANDLERS,
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'error', 'debug'],
            'propagate': False,
            'level': 'WARNING',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': LOGGING_HANDLERS,
    },
}


# Load the local settings
try:
    from local_settings import *
except:
    print "WARNING: Can not load local_settings files"
    SECRET_KEY = '&+!e83r6z$#s(^l^0im#+*7y0s%1#kz%b3qfief)%msrzid-_n'
    CERTS = {
        'default': {
            'uuid': 'f1aafae7b7764055926078b32fe81e5b',
            'public_key': """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC6B4KKFYlfMCM236RqBAs7pR+6
TtyYicTRJv/amdUSWC3LwMkZhneFx/NflaRR24DwLjoYAiVoNDFn7NEfUCyqzo0u
6daXmT95axOl7xUCpIC6TJB4kg5sZXiatvAmYURGIDC9DvbDcfpj0mAd4iVqpggw
F1xFEy/YPkMMHSqQ4wIDAQAB
-----END PUBLIC KEY-----""",
            'private_key': """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALoHgooViV8wIzbf
pGoECzulH7pO3JiJxNEm/9qZ1RJYLcvAyRmGd4XH81+VpFHbgPAuOhgCJWg0MWfs
0R9QLKrOjS7p1peZP3lrE6XvFQKkgLpMkHiSDmxleJq28CZhREYgML0O9sNx+mPS
YB3iJWqmCDAXXEUTL9g+QwwdKpDjAgMBAAECgYAFR5lI2fugG/mj4Q0FhT/cXX9d
Bkf0fFR9qyGvzpXhg2cpVTtf4hUaUuZxXAnh2Nz79BPqAoWVQ4XzcSEuRlQ+KFrD
MQ4SQnqSkLuANtyhgz5Bnlo3ioIDP5m5ZY0MTLaPS2r6AJgp8F/J8bPczDY247X6
U0mJAvBZk1HkkMOuIQJBAOr7OMWfVc8isw3oCW0chynpgmqawNjUsgj+lX94TCF1
4Rw38KYoi43d+wG3fh6ZymtrLn9WNKM38DUM1SXGiZ8CQQDKq1lDbDPzScZ1qQDu
T2pt9crK3CHgpn4hb2xEWDeZJnrDzAJrz4VxXIDVXWgmOkUgEXCg2frmsnfFkZ6m
+no9AkAjpZTJNhC4aZUsKOU1Ljy6+PeV4IAc5LdVcfmP6tnxwYYy17GkI0Z4cRJh
AksZrU7t2Mam/pbho9zGz3mOT34VAkBW9mlJ9e7gsMJYkFkW6Lq5TiNjIkvjEm3C
uQXS2auZqpo405wiWJxgxRl+9CKRbKVmmjUiwAXZ4bBk9RQHgCjdAkEAxBosr42t
0f4HxvKywdHMBvDqDzUulOmiEYFBi2D3iCXhJywTIeTTy1wdY5L+KciRvoAujrjJ
71Ejrx9zYuIiEQ==
-----END PRIVATE KEY-----""",
            'certificate': """-----BEGIN CERTIFICATE-----
MIIB7DCCAVWgAwIBAgIRALPILBkCAk5ikXGBjE2OcTEwDQYJKoZIhvcNAQEFBQAw
FzEVMBMGA1UEAxMMc3NvLmR3Ym4ub3JnMB4XDTEzMDUwNTA5MTExMloXDTE0MDUw
NTA5MTExMlowFzEVMBMGA1UEAxMMc3NvLmR3Ym4ub3JnMIGfMA0GCSqGSIb3DQEB
AQUAA4GNADCBiQKBgQC6B4KKFYlfMCM236RqBAs7pR+6TtyYicTRJv/amdUSWC3L
wMkZhneFx/NflaRR24DwLjoYAiVoNDFn7NEfUCyqzo0u6daXmT95axOl7xUCpIC6
TJB4kg5sZXiatvAmYURGIDC9DvbDcfpj0mAd4iVqpggwF1xFEy/YPkMMHSqQ4wID
AQABozgwNjAMBgNVHRMBAf8EAjAAMA4GA1UdDwEB/wQEAwIHgDAWBgNVHSUBAf8E
DDAKBggrBgEFBQcDAjANBgkqhkiG9w0BAQUFAAOBgQACeJtnoFA21qgcr3qk372Y
XznDRAGdP4gqBsiN8J3jij9j1kYNKFwaFWfua1sGAonbJRas3cezhUD57PpiQnhp
vvmsEC0q1M/PA1HgfK8YoVttgp1j2i5rCpwnMRxewK609gP+79P+j8hBBhK/c+Ho
9GB1oNtr9KHp6BpxXPo+Ag==
-----END CERTIFICATE-----"""
        }         
    }    
