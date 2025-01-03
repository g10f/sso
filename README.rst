===
SSO
===
SSO is an OpenID Connect Identity Provider with user and organisation management.
The user and organisation data are exposed via a JSONLD/Hydra Api. Api entry point is /api/

Run locally
-----------

 ``manage.py runserver``

with ssl

    INSTALLED_APPS = INSTALLED_APPS + ['django_extensions']
    SSO_USE_HTTPS = True
    SSO_DOMAIN = "localhost:8433"


    ``manage.py runserver_plus localhost:8443 --cert-file ../temp/cert``

Start a docker container
------------------------
Run

 ``docker-compose up``

or

Kubernetes with helm chart
--------------------------

.. _Helm: https://helm.sh
.. _`Helm documentation`: https://helm.sh/docs
Helm_ must be installed to use the charts. Please refer to `Helm documentation`_ to get started.

Once Helm has been set up correctly, add the repo as follows:

    helm repo add g10f https://g10f.github.io/helm-charts

If you had already added this repo earlier, run ``helm repo update`` to retrieve
the latest versions of the packages.

To install the sso chart:

    helm install my-sso g10f/sso

To uninstall the chart:

    helm delete my-sso

Prepare a development environment
----------------------------------

#) Get python >= 3.8
#) Create virtualenv for sso:  ``python3 -m venv venv``
#) Activate the virtual environment ``source venv/bin/activate``
#) Update the Python package manager ``pip install -U pip``
#) Install sso requirements in the virtualenv with: ``pip install -r requirements.txt``
#) Install postgresql ``sudo apt install postgresql``
#) Install postgis ``sudo apt install postgis``
#) Update template1 database for using citext extension:  ``sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS citext;" template1``
#) Update template1 database for using postgis extension:  ``sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" template1``
#) Create sso database user ``sudo -u postgres psql -c "CREATE USER sso CREATEDB PASSWORD 'sso'"``
#) Create empty sso database ``sudo -u postgres psql -c 'CREATE DATABASE sso OWNER sso'``
#) Create the database tables with ``./manage.py migrate``
#) Create a superuser for login ``./manage.py createsuperuser``
#) Start the develpment server with ``./manage.py runserver``

Prepare tests
-------------

#) Install selenium and uritemplate packages in the sso virtualenv ``pip install selenium`` ``pip install uritemplate``
#) Get the latest chromedriver from https://chromedriver.storage.googleapis.com/index.html and copy the binary in to a directory in the PATH (e.g. /usr/local/bin/)

Changelog
----------

Environment vars:

======================================= =========================  =========================
Name                                    default                    description
======================================= =========================  =========================
SSO_STYLE                               css/main.min.css           stylesheet
ALLOWED_HOSTS                           ''
DATABASE_NAME                           sso
DATABASE_USER                           sso
DATABASE_PASSWORD                       sso
DATABASE_CONN_MAX_AGE                   60
DATABASE_CONN_POOL                      False
DATABASE_HOST                           localhost
CACHES_LOCATION                         None
CELERY_BROKER_USE_SSL                   False
CELERY_BROKER_URL                       None
DATA_UPLOAD_MAX_MEMORY_SIZE             2621440
REGISTRATION_OPEN                       False
DEFAULT_FROM_EMAIL                      webmaster@g10f.de
STATIC_ROOT                             ../htdocs/static
MEDIA_ROOT                              ../htdocs/media
MEDIA_URL                               /media/
STATIC_URL                              /static/
SSO_THEME                               None
ROOT_URLCONF                            sso.urls
SSO_ADMIN_MFA_REQUIRED                  False
SSO_ADMIN_ONLY_MFA                      False
SSO_WEBAUTHN_USER_VERIFICATION          ''
SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT   ''
SSO_WEBAUTHN_EXTENSIONS                 False
SSO_WEBAUTHN_CREDPROPS                  False
SSO_THROTTLING_DURATION                 30
SSO_THROTTLING_MAX_CALLS                5
SSO_ADMIN_MAX_AGE                       1800                        30 min
SSO_ORGANISATION_EMAIL_DOMAIN           ''
SSO_ASYNC_EMAILS                        False
ANALYTICS_CODE                          ''
SESSION_COOKIE_AGE                      1209600                     2 weeks
SSO_2FA_HELP_URL                        ''                          external url
SSO_TOTP_TOLERANCE                      2                           tolerance of timespan
SSO_WEBAUTHN_USER_VERIFICATION          discouraged                 required value for android
======================================= =========================  =========================

3.3.23
 - fido2 version 1.1
 - switched to Fido2 only
 - fixed iOS compatibility

3.2.0
 - support for WebAuthn, allows usb-keys, fingerprint and windows hello

3.1.4
 - Docker support

3.0.1
 - django 3.1 compatibility
 - automatically create and change the signature keys with:
   `./manage.py rotate_signing_keys`
 - new settings with the following defaults
     `SSO_ACCESS_TOKEN_AGE = 60 * 60  # 1 hour`

     `SSO_ID_TOKEN_AGE = 60 * 5  # 5 minutes`

     `SSO_SIGNING_KEYS_VALIDITY_PERIOD = 60 * 60 * 24 * 30  # 30 days`

2.1.0
 - django 2.2 compatibility
 - oauthlib>=3
 - New UserNote Model
 - application specific scopes to restrict the clients which have access to user applicationroles
 - Key value table to store arbitrary user attributes. The UI/forms can be overwritten by settings.
 - new select box for administration of user applicationroles
 - support post_logout_redirect_uri of OIDC spec

1.3.1:
 - User Organisations are stored through exlicit membership class/table

1.3.0
 - PKCE support

1.2.1:
 Django 2.0 compatibility

1.0.0:
 OAuth2 and OpenID Connect Support

1.2.0:
 Organisation Data Management

1.1.0:
 JSONLD/Hydra Api
