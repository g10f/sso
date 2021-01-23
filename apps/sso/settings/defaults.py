import os
from uuid import UUID

import sys

from django.urls import reverse_lazy
from django.utils.translation import pgettext_lazy

try:
    RUNNING_DEVSERVER = (sys.argv[1] == 'runserver')
except IndexError:
    RUNNING_DEVSERVER = False

RUNNING_TEST = 'test' in sys.argv

if RUNNING_DEVSERVER or RUNNING_TEST:
    INTERNAL_IPS = ['127.0.0.1', '[::1]']
    DEBUG = True
else:
    DEBUG = False

ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]']

THUMBNAIL_QUALITY = 100
THUMBNAIL_FORMAT = 'PNG'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SITE_ID = 1
DEFAULT_FROM_EMAIL = 'webmaster@g10f.de'
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3  # new default in django 3
SSO_BRAND = 'G10F'
SSO_SITE_NAME = 'G10F'
SSO_DOMAIN = "localhost:8000"
SSO_USE_HTTPS = False
SSO_SERVICE_DOCUMENTATION = ""  # part of http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
SSO_ABOUT = 'http://g10f.de/'
SSO_DATA_PROTECTION_URI = None
SSO_APP_UUID = UUID('fa467234b81e4838a009e38d9e655d18')
SSO_BROWSER_CLIENT_ID = UUID('ca96cd88bc2740249d0def68221cba88')
SSO_STYLE = 'default'
SSO_STYLE_VERSION = '1.1.0'
SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES = 60
SSO_DEFAULT_MEMBER_PROFILE_UUID = UUID('b4caab335bbc4c90a6f552f7f13aa410')
SSO_DEFAULT_GUEST_PROFILE_UUID = UUID('9859f78da9a44491bf3d807d10993ce7')
SSO_DEFAULT_ADMIN_PROFILE_UUID = UUID('1593284b238c4a1cabf291e573205508')
SSO_SHOW_ADDRESS_AND_PHONE_FORM = True  # Address and Phone number in profile form
SSO_VALIDATION_PERIOD_IS_ACTIVE = False  # accounts must not be prolonged
SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL = False  # all accounts must be prolonged, not only account from marked centers
SSO_VALIDATION_PERIOD_DAYS = 365  # accounts must be prolonged after 1 year
SSO_ADMIN_MAX_AGE = 60 * 30  # 30 min max age for admin pages
SSO_ORGANISATION_EMAIL_DOMAIN = ''
SSO_ORGANISATION_EMAIL_MANAGEMENT = False
SSO_ORGANISATION_REQUIRED = False
SSO_REGION_MANAGEMENT = False
SSO_COUNTRY_MANAGEMENT = False
SSO_GOOGLE_GEO_API_KEY = 'insert your key'
SSO_EMAIL_LOGO = ""
SSO_ASYNC_EMAILS = False  # send emails async via celery task
SSO_NOREPLY_EMAIL = 'webmaster@g10f.de'
SSO_POST_RESET_LOGIN = True
# configured default forms and functions
SSO_ADMIN_UPDATE_USER_FORM = 'sso.accounts.forms.UserProfileForm'
SSO_ADMIN_ADD_USER_FORM = 'sso.accounts.forms.UserAddForm'
SSO_SELF_REGISTRATION_FORM = 'sso.accounts.forms.UserSelfRegistrationForm2'
SSO_ADMIN_REGISTRATION_PROFILE_FORM = 'sso.registration.forms.RegistrationProfileForm'
SSO_DEFAULT_IDTOKEN_FINALIZER = 'sso.oauth2.oidc_token.default_idtoken_finalizer'
SSO_DEFAULT_TOKEN_GENERATOR = 'sso.oauth2.oidc_token.default_token_generator'
SSO_TEST_USER_EXTRA_ATTRIBUTES = []
SSO_USER_RECOVERY_PERIOD_MINUTES = 60 * 24 * 30  # 30 days
SSO_OIDC_SESSION_COOKIE_NAME = 'oidcsession'
OTP_DEVICES = [
    'sso_auth.TOTPDevice',
    'sso_auth.U2FDevice',
]
SSO_ADMIN_ONLY_2F = False

# Celery settings see https://www.cloudamqp.com/docs/celery.html
CELERY_BROKER_USE_SSL = False
CELERY_BROKER_URL = None  # 'amqp://guest:guest@localhost//'
CELERY_BROKER_POOL_LIMIT = 1  # Will decrease connection usage
CELERY_BROKER_HEARTBEAT = None
CELERY_BROKER_CONNECTION_TIMEOUT = 30  # May require a long timeout due to Linux DNS timeouts etc
CELERY_RESULT_BACKEND = None
CELERY_WORKER_SEND_TASK_EVENTS = False  # Will not create celeryev.* queues
# CELERY_EVENT_QUEUE_EXPIRES = 60  # Will delete all celeryev. queues without consumers after 1 minute.
#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Publishing Broker
BROKER_USE_SSL = CELERY_BROKER_USE_SSL
BROKER_URL = CELERY_BROKER_URL

EMAIL_SUBJECT_PREFIX = '[SSO] '

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

ADMINS = (
    ('Gunnar Scherf', 'webmaster@g10f.de'),
)
MANAGERS = ADMINS

CENTER_TYPE_CHOICES = (
    ('g', pgettext_lazy('Organisation Type', 'Group')),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'sso',
        'USER': 'sso',
        'PASSWORD': 'sso',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 60
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 300,
        'KEY_PREFIX': 'sso'
    }
}

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'

ABSOLUTE_URL_OVERRIDES = {
    'accounts.user': lambda u: "/api/v2/users/%s/" % u.uuid.hex,
}

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(BASE_DIR)), 'htdocs/static')
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.abspath(BASE_DIR)), 'htdocs/media')

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

if DEBUG:
    # don't use cached loader
    LOADERS = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]
else:
    LOADERS = [
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        # 'APP_DIRS': True,  # must not be set if loaders is set
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'sso.context_processors.settings',
            ],
            'loaders': LOADERS,
            'debug': DEBUG
        },
    },
]

MIDDLEWARE = [
    'sso.oauth2.middleware.SsoSessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'sso.oauth2.middleware.OAuthAuthenticationMiddleware',
    'sso.auth.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'current_user.middleware.CurrentUserMiddleware',
    'sso.middleware.TimezoneMiddleware',
    'sso.middleware.RevisionMiddleware'
]

ROOT_URLCONF = 'sso.urls'
APPEND_SLASH = True

INSTALLED_APPS = [
    'sso',
    'sso.forms',
    'password',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.gis',
    'django.forms',
    'formtools',
    'sorl.thumbnail',
    'captcha',
    'l10n',
    'smart_selects',
    'reversion',
    'sso.emails',
    'sso.organisations',
    'sso.accounts',
    'sso.registration',
    'sso.auth',
    'sso.oauth2',
    'sso.api',
    'sso.access_requests',
]

DEFAULT_AUTHENTICATION_BACKEND = 'sso.auth.backends.EmailBackend'

AUTHENTICATION_BACKENDS = (
    DEFAULT_AUTHENTICATION_BACKEND,
    'sso.oauth2.backends.OAuth2Backend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
)

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = reverse_lazy('auth:login')
LOGOUT_URL = reverse_lazy('auth:logout')
AUTH_USER_MODEL = 'accounts.User'

REGISTRATION = {
    'OPEN': False,
    'TOKEN_EXPIRATION_DAYS': 7,
    'ACTIVATION_EXPIRATION_DAYS': 60,
    'CONTACT_EMAIL': DEFAULT_FROM_EMAIL,
}

# with AWS SES e.g can only send from verified emails
# https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html
SSO_SEND_FROM_VERIFIED_EMAIL_ADDRESSES = '%s|%s|%s' % \
                                         (DEFAULT_FROM_EMAIL, SSO_NOREPLY_EMAIL, REGISTRATION['CONTACT_EMAIL'])

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error', 'admin.E408', 'admin.E410']

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
SESSION_ENGINE = 'sso.sessions.backends.jwt_cookies'
CSRF_FAILURE_VIEW = 'sso.views.csrf.csrf_failure'

if not (RUNNING_DEVSERVER or RUNNING_TEST):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

AUTH_PASSWORD_VALIDATORS = [{
    'NAME': 'password.validation.MinimumLengthValidator',
}, {
    'NAME': 'password.validation.CommonPasswordValidator',
}, {
    'NAME': 'password.validation.DigitsValidator'
}]

# overwrite this if integration with other associations is required
SSO_DEFAULT_ASSOCIATION_UUID = UUID('bad2e6edff274f2f900ff3dbb26e38ce')
kid1 = '25e96efa6c654585b3f12986b355e42f'
SIGNING = {
    'HS256': {
        'active': kid1,
        'keys': {
            kid1: {
                'SECRET_KEY': '$20e%(in^nv_-&syxvx4$1%()nfx$dx@)omf)0i-%je&w!((^e',
            }
        }
    },
    'RS256': {
        'active': kid1,
        'keys': {
            kid1: {
                'public_key': """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu8TOBiOu0mR499t8W+N6
Y85zNl+puP+GSWzgoIclYDKrWCFZWVp164gHpShB3dp2dH9wpDH0fAh7AackrOiC
temis3bTpCSbR7vJbKck3OBDgdMSvefGMwgOEvvptouEAKBSMqpAoASYpRWPC1f5
W7K584+UOUMcLr/vHf2WFZMZCgbaTENAedbdUZZJplrz5rL5FTmYzWRzwmghI6SA
FjV/SE85zjMJVtsGCCQF8fZZrcdZ6KJNNWOm2T7xIb/OqKvPhsqwRP8RVIIREoM7
1PklpRtoLlbZ9LR/wKN6R4MrlZBtZDRKuW8mlnhEHhnj/ErvDI/K1zsDpMupWUUP
MwIDAQAB
-----END PUBLIC KEY-----
""",
                'SECRET_KEY': """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAu8TOBiOu0mR499t8W+N6Y85zNl+puP+GSWzgoIclYDKrWCFZ
WVp164gHpShB3dp2dH9wpDH0fAh7AackrOiCtemis3bTpCSbR7vJbKck3OBDgdMS
vefGMwgOEvvptouEAKBSMqpAoASYpRWPC1f5W7K584+UOUMcLr/vHf2WFZMZCgba
TENAedbdUZZJplrz5rL5FTmYzWRzwmghI6SAFjV/SE85zjMJVtsGCCQF8fZZrcdZ
6KJNNWOm2T7xIb/OqKvPhsqwRP8RVIIREoM71PklpRtoLlbZ9LR/wKN6R4MrlZBt
ZDRKuW8mlnhEHhnj/ErvDI/K1zsDpMupWUUPMwIDAQABAoIBACW2ipbLFfLmATHv
IJQoJU3killyb1lb4THgL2Guo0AmDSofUJ3UwHh1EuwGIOyZU09kxVAFRJCg92vG
kWQ1MwOskGQxSqLeQ13uBq/PBmVimcx6g3onEjTvujvv4uoqLXIewUOx1FcPdUU7
BkcF/WyAgj68KM4zf3aYUEOaykk8sR+dIFR1+V6VlHugJyNo+NZdyJHqW/zj2Vxw
DcoOZfe5+hZc3bWAcqFKIjcIRXV5oOKWvJ0Obo3CftFeWSSXd3R4+KT53Bo6obqx
uFtIKcE+hIa2CTxWUNbK2Mia/5yZyicVkeZWb2lCUoj9rMbiVAsxn/C51aMaI1m4
G2pcN1ECgYEA4c2SmILTNibKrjV2C4gm5RGGo3va/09qMextC37oCR97RkcIxOHp
caMOJkAbbNJQdAprM5it4/33a2J86LuYKA2iNYWyGAb5gNo319nQZ23YGSjQIqpx
XPwzBjnvwmAALibIzm093e4iVfH4+V71/ZpUvk0szMup5deKy8W6lisCgYEA1OEe
jHoZ+/Xo8S6W8O+BZk4mYmbr7vGaD2t+EMKCFHlxCrENHw0JHk9pdpnVhFaRmvOr
g84YtZs2O216UQBUk2lCuCt74KWq73UllObFhNnKuLdx/pRWz5Xteu/nJ8KcMzDS
iCdJFfZ2G6sp+eN3yFMcCNUiapuRTVYpXoKvrxkCgYBEtlDg1ha9yMoufxg/5Bup
405sW1lGDf2L2Z1JPUIQ3KKfvSf++ZwXN34rx6BQ2iMfXLhIiDKKSZNL+zl1fPiN
X7C3xspuI1kzi7QonCCeCMAUz+WeVu2OVTSVtXWvWZVUdfrvTjDgYwHR04NnJy2G
Ebut+UAjxeoahh+3aKEh5wKBgHJn7fgHIvHTTfZYWIxx2zQ1KdHWiFOpCmfhGCY/
spL4VTUuw+N9KPpeKUqxEBwIPkZtUC8M0yC+op27j3H64Hk8p7u8ut2Xi08XwTPN
9jcYqScuh5gO9rynUbKxPaSTpUipo2vC2TdxdjYWff+rLNO/PqDMkquCoctTU/ZT
+8D5AoGABn8e+q6jbHsy0dJzKIoUqJ81RDVYhtc7yWZt0pA2IbSjWpdXCNNxUEuq
NcWSqklhLQ5S932UzPFw3iDaDdR3/6DwG7wi8mZiVSWlBbLHIOMMzKvszVfJvDcI
LLdXzhLAb/qsleh83t/tLENwOIF5PnaFihbYJ7i4THgYqmYeN+o=
-----END RSA PRIVATE KEY-----
"""
            }
        }
    }
}

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
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'sso': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'sorl': {
            'level': 'INFO',
        },
        'oauthlib': {
            'level': 'INFO',
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'mail_admins'],
    },
}