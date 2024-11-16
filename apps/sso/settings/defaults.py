import os
import sys
from pathlib import Path
from uuid import UUID
from warnings import filterwarnings

from django.urls import reverse_lazy
from django.utils.translation import pgettext_lazy

try:
    RUNNING_DEVSERVER = (sys.argv[1] in ['runserver', 'runserver_plus'])
    RUNNING_DEVSERVER_PLUS = (sys.argv[1] in ['runserver_plus'])
except IndexError:
    RUNNING_DEVSERVER = False
    RUNNING_DEVSERVER_PLUS = False

RUNNING_TEST = 'test' in sys.argv

if RUNNING_DEVSERVER or RUNNING_TEST:
    INTERNAL_IPS = ['127.0.0.1', '[::1]']
    DEBUG = True
else:
    DEBUG = False
DEBUG = os.getenv("DEBUG", str(DEBUG)).lower() in ('true', '1', 't')

ALLOWED_HOSTS = ['.localhost', '127.0.0.1', '[::1]'] + os.getenv('ALLOWED_HOSTS', '').split(',')
SSO_STYLE = os.getenv('SSO_STYLE', 'css/main.min.css')

THUMBNAIL_QUALITY = 100
THUMBNAIL_FORMAT = 'PNG'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SITE_ID = 1
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'gunnar.scherf@gmail.com')
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3  # new default in django 3
SSO_BRAND = 'G10F'
SSO_SITE_NAME = os.getenv('SSO_SITE_NAME', "G10F")
SSO_DOMAIN = os.getenv('SSO_DOMAIN', "localhost:8000")
SSO_USE_HTTPS = os.getenv("SSO_USE_HTTPS", 'True').lower() in ('true', '1', 't')
SSO_SERVICE_DOCUMENTATION = ""  # part of https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
SSO_ABOUT = os.getenv('SSO_ABOUT', "https://g10f.de/")
SSO_2FA_HELP_URL = os.getenv('SSO_2FA_HELP_URL', "")
SSO_DATA_PROTECTION_URI = None
SSO_APP_UUID = UUID('fa467234b81e4838a009e38d9e655d18')
SSO_BROWSER_CLIENT_ID = UUID('ca96cd88bc2740249d0def68221cba88')
SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES = 60
SSO_DEFAULT_MEMBER_PROFILE_UUID = UUID('b4caab335bbc4c90a6f552f7f13aa410')
SSO_DEFAULT_GUEST_PROFILE_UUID = UUID('9859f78da9a44491bf3d807d10993ce7')
SSO_DEFAULT_ADMIN_PROFILE_UUID = UUID('1593284b238c4a1cabf291e573205508')
SSO_SHOW_ADDRESS_AND_PHONE_FORM = True  # Address and Phone number in profile form
SSO_VALIDATION_PERIOD_IS_ACTIVE = False  # accounts must not be prolonged
SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL = False  # all accounts must be prolonged, not only account from marked centers
SSO_VALIDATION_PERIOD_DAYS = 365  # accounts must be prolonged after 1 year
SSO_ADMIN_MAX_AGE = int(os.getenv("SSO_ADMIN_MAX_AGE", '1800'))  # 30 min max age for admin pages
SSO_ORGANISATION_EMAIL_DOMAIN = os.getenv("SSO_ORGANISATION_EMAIL_DOMAIN", '')
SSO_ORGANISATION_EMAIL_MANAGEMENT = False
SSO_ORGANISATION_REQUIRED = False
SSO_REGION_MANAGEMENT = False
SSO_COUNTRY_MANAGEMENT = False
SSO_GOOGLE_GEO_API_KEY = os.getenv('SSO_GOOGLE_GEO_API_KEY')
SSO_EMAIL_LOGO = ""
SSO_ASYNC_EMAILS = os.getenv("SSO_ASYNC_EMAILS", 'False').lower() in ('true', '1', 't')  # send emails async via celery task
SSO_NOREPLY_EMAIL = os.getenv('SSO_NOREPLY_EMAIL', 'gunnar.scherf@gmail.com')
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
SSO_ACCESS_TOKEN_AGE = 60 * 60  # 1 hour
SSO_ID_TOKEN_AGE = 60 * 5  # 5 minutes
SSO_LOGIN_MAX_AGE = int(os.getenv('SSO_LOGIN_MAX_AGE', '300'))
SSO_SIGNING_KEYS_VALIDITY_PERIOD = 60 * 60 * 24 * 30  # 30 days
SSO_USER_MAX_PICTURE_SIZE = int(os.getenv('SSO_USER_MAX_PICTURE_SIZE', '1048576'))
SSO_USER_PICTURE_WIDTH = 550
SSO_USER_PICTURE_HEIGHT = 550
SSO_USER_PICTURE_REQUIRED = os.getenv("SSO_USER_PICTURE_REQUIRED", 'False').lower() in ('true', '1', 't')
SSO_OIDC_SESSION_COOKIE_NAME = 'oidcsession'
SSO_TOTP_TOLERANCE = int(os.getenv('SSO_TOTP_TOLERANCE', '2'))
SSO_ADMIN_ONLY_MFA = os.getenv("SSO_ADMIN_ONLY_MFA", 'False').lower() in ('true', '1', 't')
SSO_ADMIN_MFA_REQUIRED = os.getenv("SSO_ADMIN_MFA_REQUIRED", 'False').lower() in ('true', '1', 't')
SSO_WEBAUTHN_VERSION = os.getenv('SSO_WEBAUTHN_VERSION', 'FIDO_2_0')  # "U2F_V2", "FIDO_2_0"
SSO_WEBAUTHN_USER_VERIFICATION = os.getenv('SSO_WEBAUTHN_USER_VERIFICATION', 'discouraged')
SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT = os.getenv('SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT', '')
SSO_WEBAUTHN_EXTENSIONS = os.getenv("SSO_WEBAUTHN_EXTENSIONS", 'False').lower() in ('true', '1', 't')
SSO_WEBAUTHN_CREDPROPS = os.getenv("SSO_WEBAUTHN_CREDPROPS", 'False').lower() in ('true', '1', 't')
SSO_RECAPTCHA_EXPIRATION_TIME = 120
SSO_RECAPTCHA_ENABLED = os.getenv("SSO_RECAPTCHA_ENABLED", 'True').lower() in ('true', '1', 't')
SSO_THROTTLING_DURATION = int(os.getenv('SSO_THROTTLING_DURATION', '30'))
SSO_THROTTLING_MAX_CALLS = int(os.getenv('SSO_THROTTLING_MAX_CALLS', '5'))
SSO_DEFAULT_THEME = os.getenv("SSO_DEFAULT_THEME", 'auto')
SSO_ENABLE_PLAUSIBLE = os.getenv('SSO_ENABLE_PLAUSIBLE', 'False').lower() in ('true', '1', 't')
# Celery settings see https://www.cloudamqp.com/docs/celery.html
CELERY_BROKER_USE_SSL = os.getenv("CELERY_BROKER_USE_SSL", 'True').lower() in ('true', '1', 't')
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')  # 'amqp://guest:guest@localhost//'
CELERY_BROKER_POOL_LIMIT = 1  # Will decrease connection usage
CELERY_BROKER_HEARTBEAT = None
CELERY_BROKER_CONNECTION_TIMEOUT = 30  # May require a long timeout due to Linux DNS timeouts etc
CELERY_RESULT_BACKEND = None
CELERY_WORKER_SEND_TASK_EVENTS = False  # Will not create celeryev.* queues
# CELERY_EVENT_QUEUE_EXPIRES = 60  # Will delete all celeryev. queues without consumers after 1 minute.
# Only add pickle to this list if your broker is secured
# from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

ANALYTICS = {'ANALYTICS_CODE': os.getenv('ANALYTICS_CODE', '')}

EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', '[SSO] ')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'root@localhost')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

ADMINS = (
    ('Gunnar Scherf', 'gunnar.scherf@gmail.com'),
)
MANAGERS = ADMINS

CENTER_TYPE_CHOICES = (
    ('g', pgettext_lazy('Organisation Type', 'Group')),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('DATABASE_NAME', 'sso'),
        'USER': os.getenv('DATABASE_USER', 'sso'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'sso'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': '5432'
    },
}

if os.getenv("DATABASE_CONN_POOL", 'False').lower() in ('true', '1', 't'):
    DATABASES['default']['OPTIONS'] = {"pool": True}
else:
    # CONN_MAX_AGE can only be used without connection pooling
    DATABASES['default']['CONN_MAX_AGE'] = int(os.getenv('DATABASE_CONN_MAX_AGE', '60'))

if os.getenv('CACHES_LOCATION') is not None:
    CACHES = {
        'default': {
            'BACKEND': 'sso.cache.backends.SSOCache',
            'LOCATION': os.getenv('CACHES_LOCATION').split(','),
            'TIMEOUT': 300,
            'KEY_PREFIX': 'sso'}}

DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', '2621440'))  # i.e. 2.5 MB

# see captcha.constants
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY', "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI")
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe")

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'

ABSOLUTE_URL_OVERRIDES = {
    'accounts.user': lambda u: "/api/v2/users/%s/" % u.uuid.hex,
}

# Default from django 5.0
USE_TZ = True

STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR.parent / 'htdocs/static')
MEDIA_ROOT = os.getenv('MEDIA_ROOT', BASE_DIR.parent / 'htdocs/media')

MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
STATIC_URL = os.getenv('STATIC_URL', '/static/')

if RUNNING_TEST:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.InMemoryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

WHITENOISE_ROOT = os.path.join(STATIC_ROOT, 'root')
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
    'sso.middleware.RevisionMiddleware',
    # 'silk.middleware.SilkyMiddleware'
]
# SILKY_PYTHON_PROFILER = True
ROOT_URLCONF = os.getenv('ROOT_URLCONF', 'sso.urls')
APPEND_SLASH = True

INSTALLED_APPS = [
    'sso',
    'sso.forms',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    "whitenoise.runserver_nostatic",
    'django.contrib.staticfiles',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.gis',
    'django.forms',
    # 'silk',
    'formtools',
    'sorl.thumbnail',
    'django_recaptcha',
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
    'sso.components'
]
if os.getenv('SSO_THEME') is not None:
    INSTALLED_APPS.insert(0, os.getenv('SSO_THEME'))

if RUNNING_DEVSERVER_PLUS:
    INSTALLED_APPS = INSTALLED_APPS + ['django_extensions']

DEFAULT_AUTHENTICATION_BACKEND = 'sso.auth.backends.EmailBackend'

AUTHENTICATION_BACKENDS = (
    DEFAULT_AUTHENTICATION_BACKEND,
    'sso.oauth2.backends.OAuth2Backend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
)

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = reverse_lazy('auth:login')
LOGOUT_URL = reverse_lazy('auth:logout')
AUTH_USER_MODEL = 'accounts.User'

REGISTRATION = {
    'OPEN': os.getenv("REGISTRATION_OPEN", 'False').lower() in ('true', '1', 't'),
    'TOKEN_EXPIRATION_DAYS': 7,
    'ACTIVATION_EXPIRATION_DAYS': 30,
    'CONTACT_EMAIL': DEFAULT_FROM_EMAIL,
}

# with AWS SES e.g can only send from verified emails
# https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html
SSO_SEND_FROM_VERIFIED_EMAIL_ADDRESSES = '%s|%s|%s' % (DEFAULT_FROM_EMAIL, SSO_NOREPLY_EMAIL, REGISTRATION['CONTACT_EMAIL'])

SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", f'{60 * 60 * 24 * 7 * 2}'))  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
SESSION_ENGINE = 'sso.sessions.backends.jwt_cookies'
CSRF_COOKIE_HTTPONLY = os.getenv('CSRF_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 't')

if not (RUNNING_DEVSERVER or RUNNING_TEST):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# silence RemovedInDjango60Warning
filterwarnings("ignore", "The FORMS_URLFIELD_ASSUME_HTTPS transitional setting is deprecated.")
FORMS_URLFIELD_ASSUME_HTTPS = True

AUTH_PASSWORD_VALIDATORS = [{
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    'OPTIONS': {
        'min_length': int(os.getenv('SSO_PASSWORD_MINIMUM_LENGTH', '8')), }}, {
    'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}
]

# overwrite this if integration with other associations is required
SSO_DEFAULT_ASSOCIATION_UUID = UUID('bad2e6edff274f2f900ff3dbb26e38ce')

# set this in local_settings.py or by env var
SECRET_KEY = os.getenv("SECRET_KEY")

# Logging
LOGGING_LEVEL_DB = os.getenv('LOGGING_LEVEL_DB', 'INFO')
LOGGING_LEVEL_SSO = os.getenv('LOGGING_LEVEL_SSO', 'DEBUG' if DEBUG else 'INFO')
LOGGING_LEVEL_ROOT = os.getenv('LOGGING_LEVEL_ROOT', 'INFO')
LOGGING_LEVEL_DJANGO = os.getenv('LOGGING_LEVEL_DJANGO', 'INFO')

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
            'level': LOGGING_LEVEL_DJANGO,
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'mail_admins'],
            'level': LOGGING_LEVEL_DB,
            'propagate': False,
        },
        'sso': {
            'handlers': ['console', 'mail_admins'],
            'level': LOGGING_LEVEL_SSO,
            'propagate': False,
        },
    },
    'root': {
        'level': LOGGING_LEVEL_ROOT,
        'handlers': ['console', 'mail_admins'],
    },
}
