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

BRAND = 'G10F'
DEV_MASCHINE_NAME = 'G10F-1'
ABOUT = 'http://g10f.de/'
APP_UUID = 'fa467234b81e4838a009e38d9e655d18'
STREAMING_UUID = 'c362bea58c67457fa32234e3178285c4'

DIRNAME = os.path.join(os.path.dirname(__file__), '..')

hostname = socket.gethostname().upper()
TEST = 'test' in sys.argv

ADMINS = (
    ('Gunnar Scherf', 'gunnar.scherf@gmail.com'),
)
MANAGERS = ADMINS
USER_CHANGE_EMAIL_RECIPIENT_LIST = ['gunnar.scherf@gmail.com']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'sso',
        'USER': 'sso',
        'PASSWORD': 'sso',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 60
    },
}

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de-de'

ABSOLUTE_URL_OVERRIDES = {
    'accounts.user': lambda u: "/api/v1/users/%s/" % u.uuid,
}

SITE_ID = 1

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = os.path.join(DIRNAME, '../../../static/htdocs/sso/static')
MEDIA_ROOT = os.path.join(DIRNAME, '../../../static/htdocs/sso/media')

STATICFILES_DIRS = (
    os.path.join(DIRNAME, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
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
    os.path.join(DIRNAME, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',  # needed for send_account_created_email in accounts
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'sorl.thumbnail',
    'passwords',
    'l10n',
    'south',
    'streaming',
    'sso',
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
    os.path.join(DIRNAME, 'locale'),
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

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
AUTH_USER_MODEL = 'accounts.User'

ACCOUNT_ACTIVATION_DAYS = 1

REGISTRATION = {
    'OPEN': False,
}

SESSION_COOKIE_AGE = 60 * 20  # seconds * Minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
SESSION_ENGINE = 'sso.sessions.backends'  # 'django.contrib.sessions.backends.signed_cookies'
#SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies' 
if not LOCAL_DEV:
    SESSION_COOKIE_SECURE = True

PASSWORD_COMPLEXITY = {  # You can ommit any or all of these for no limit for that particular set
    "UPPER": 0,       # Uppercase
    "LOWER": 0,       # Lowercase
    "DIGITS": 1,      # Digits
    "PUNCTUATION": 0,  # Punctuation (string.punctuation)
    "NON ASCII": 0,   # Non Ascii (ord() >= 128)
    "WORDS": 0        # Words (substrings seperates by a whitespace)
}

#Configure logging
if DEBUG:
    LOGGING_LEVEL = 'DEBUG'
else:
    DEFAULT_FROM_EMAIL = 'webmaster@dwbn.org'
    LOGGING_LEVEL = 'INFO'

LOGGING_HANDLERS = ['mail_admins', 'error', ]
if DEBUG:
    LOGGING_HANDLERS += ['debug', 'console']

ERROR_LOGFILE = "../../../logs/sso-django-error.log"
INFO_LOGFILE = "../../../logs/sso-django-info.log"

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
            'filename': os.path.join(DIRNAME, ERROR_LOGFILE),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(DIRNAME, INFO_LOGFILE),
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
            'handlers': ['mail_admins'],
            'level': 'ERROR',
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
