# -*- coding: utf-8 -*-
# Django settings for sso project.
import os
import sys
from uuid import UUID
from django.urls import reverse_lazy

try:
    RUNNING_DEVSERVER = (sys.argv[1] == 'runserver')
except:
    RUNNING_DEVSERVER = False

RUNNING_TEST = 'test' in sys.argv

if RUNNING_DEVSERVER:
    INTERNAL_IPS = ('127.0.0.1',)
    DEBUG = True
else:
    DEBUG = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # django 1.7 settings

SSO_BRAND = 'G10F'
SSO_SITE_NAME = 'G10F'
SSO_BASE_URL = 'http://localhost:8000'  # for management scripts without a request object
SSO_SERVICE_DOCUMENTATION = ""  # part of http://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
SSO_ABOUT = 'http://g10f.de/'
SSO_APP_UUID = UUID('fa467234b81e4838a009e38d9e655d18')
SSO_BROWSER_CLIENT_ID = UUID('ca96cd88bc2740249d0def68221cba88')
SSO_STREAMING_UUID = UUID('c362bea58c67457fa32234e3178285c4')
SSO_STYLE = 'default'
SSO_STYLE_VERSION = '1.0.19'
SSO_LESS = False
SSO_FAVICON = 'ico/favicon.ico'
SSO_EMAIL_CONFIRM_TIMEOUT_MINUTES = 60
SSO_DEFAULT_ROLE_PROFILE_UUID = UUID('b4caab335bbc4c90a6f552f7f13aa410')
SSO_DEFAULT_GUEST_PROFILE_UUID = UUID('9859f78da9a44491bf3d807d10993ce7')
SSO_DEFAULT_ADMIN_PROFILE_UUID = UUID('1593284b238c4a1cabf291e573205508')
SSO_SHOW_ADDRESS_AND_PHONE_FORM = True  # Address and Phone number in profile form
SSO_VALIDATION_PERIOD_IS_ACTIVE = True  # accounts must be prolonged
SSO_VALIDATION_PERIOD_IS_ACTIVE_FOR_ALL = False  # all accounts must be prolonged, not only account from marked centers
SSO_VALIDATION_PERIOD_DAYS = 365  # accounts must be prolonged after 1 year
SSO_ADMIN_MAX_AGE = 60 * 30  # 30 min max age for admin pages
SSO_ORGANISATION_EMAIL_DOMAIN = '@g10f.de'
SSO_ORGANISATION_EMAIL_MANAGEMENT = False
SSO_REGION_MANAGEMENT = False
SSO_COUNTRY_MANAGEMENT = False
SSO_GOOGLE_GEO_API_KEY = 'insert your key'
SSO_EMAIL_LOGO = ""
SSO_DOMAIN = "sso.g10f.de"
SSO_USE_HTTPS = True
SSO_ASYNC_EMAILS = False  # send emails async via celery task
SSO_NOREPLY_EMAIL = None

OTP_DEVICES = [
    'sso_auth.TOTPDevice',
    'sso_auth.U2FDevice',
    # 'sso_auth.TwilioSMSDevice',
]

OTP_TWILIO_ACCOUNT = ''
OTP_TWILIO_AUTH = ''
OTP_TWILIO_FROM = ''
OTP_TWILIO_NO_DELIVERY = True
OTP_TWILIO_TOKEN_VALIDITY = 300  # seconds

# Celery settings see https://www.cloudamqp.com/docs/celery.html
BROKER_USE_SSL = False
BROKER_URL = 'amqp://guest:guest@localhost//'
BROKER_POOL_LIMIT = 1  # Will decrease connection usage
BROKER_HEARTBEAT = None
BROKER_CONNECTION_TIMEOUT = 30  # May require a long timeout due to Linux DNS timeouts etc
CELERY_RESULT_BACKEND = None
CELERY_SEND_EVENTS = False  # Will not create celeryev.* queues
# CELERY_EVENT_QUEUE_EXPIRES = 60  # Will delete all celeryev. queues without consumers after 1 minute.
#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

EMAIL_SUBJECT_PREFIX = '[SSO] '

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

ADMINS = (
    ('Gunnar Scherf', 'webmaster@g10f.de'),
)
MANAGERS = ADMINS
USER_CHANGE_EMAIL_RECIPIENT_LIST = ['webmaster@g10f.de']
DEFAULT_FROM_EMAIL = 'webmaster@g10f.de'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # 'django.db.backends.postgresql',
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

STATIC_ROOT = os.path.join(BASE_DIR, '../../static/htdocs/sso/static')
MEDIA_ROOT = os.path.join(BASE_DIR, '../../static/htdocs/sso/media')

LOCALE_PATHS = ()
STATICFILES_DIRS = ()

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
        'DIRS': [
        ],
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'sso.oauth2.middleware.OAuthAuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',  # Allows a user’s sessions to be invalidated when their password changes.
    'sso.auth.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'current_user.middleware.CurrentUserMiddleware',
    'sso.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'sso.urls'

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
    'nocaptcha_recaptcha',
    'l10n',
    'smart_selects',
    'sso.emails',
    'sso.organisations',
    'sso.accounts',
    'sso.registration',
    'sso.auth',
    'sso.oauth2',
    'sso.api',
]

THUMBNAIL_QUALITY = 100

L10N_SETTINGS = {
    'currency_formats': {
        'USD': {'symbol': u'$', 'positive': u"$%(val)0.2f", 'negative': u"-$%(val)0.2f", 'decimal': '.'},
        'GBP': {'symbol': u'£', 'positive': u"£%(val)0.2f", 'negative': u"-£%(val)0.2f", 'decimal': '.'},
        'EURO': {'symbol': u'€', 'positive': u"%(val)0.2f €", 'negative': u"-%(val)0.2f €", 'decimal': ','},
    },
    'default_currency': 'EURO',
}

AUTHENTICATION_BACKENDS = (
    'sso.auth.backends.EmailBackend',
    'sso.oauth2.backends.OAuth2Backend',
)

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
)
POSTGIS_VERSION = (2, 0, 3)

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = reverse_lazy('auth:login')
LOGOUT_URL = reverse_lazy('accounts:logout')
AUTH_USER_MODEL = 'accounts.User'

REGISTRATION = {
    'OPEN': False,
    'TOKEN_EXPIRATION_DAYS': 7,
    'ACTIVATION_EXPIRATION_DAYS': 60,
    'CONTACT_EMAIL': DEFAULT_FROM_EMAIL,
}

NORECAPTCHA_SITE_KEY = '6LccjewSAAAAAPcFZmUtuzRVkU6hhOona0orqgKh'
NORECAPTCHA_SECRET_KEY = '6LccjewSAAAAAAhJzHuEyVV40AYApL6CpmjqlmX8'

SESSION_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False
SESSION_ENGINE = 'sso.sessions.backends.jwt_cookies'
# SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = None
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

# overwrite the secrets in your local_settings.py
SECRET_KEY = '7pvncv391)#rz%dhocfmic_#+(p**284lnsx2j#s)$n5ln-hnk'
CERTS = {
    'default': {
        'uuid': 'f1aafae7b7764055926078b32fe81e5b',
        'public_key': """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC6B4KKFYlfMCM236RqBAs7pR+6
TtyYicTRJv/amdUSWC3LwMkZhneFx/NflaRR24DwLjoYAiVoNDFn7NEfUCyqzo0u
6daXmT95axOl7xUCpIC6TJB4kg5sZXiatvAmYURGIDC9DvbDcfpj0mAd4iVqpggw
F1xFEy/YPkMMHSqQ4wIDAQAB
-----END PUBLIC KEY-----""",
        'PRIVATE_KEY': """-----BEGIN PRIVATE KEY-----
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

# Load the local settings
try:
    from .local_settings import *
except:
    print("WARNING: Can not load local_settings files")
