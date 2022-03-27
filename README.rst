===
SSO
===
SSO is an OpenID Connect Identity Provider with user and organisation management.
The user and organisation data are exposed via a JSONLD/Hydra Api. Api entry point is /api/

Start a docker container
------------------------
Run

 ``docker-compose up``

or

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

===========================  =========================  =========================
Name                         default                    description
===========================  =========================  =========================
SSO_STYLE                    css/main.min.css           stylesheet
ALLOWED_HOSTS                ''
DATABASE_NAME                sso
DATABASE_USER                sso
DATABASE_PASSWORD            sso
DATABASE_CONN_MAX_AGE        60
DATABASE_HOST                localhost
CACHES_LOCATION              None
CELERY_BROKER_USE_SSL        False
CELERY_BROKER_URL            None
DATA_UPLOAD_MAX_MEMORY_SIZE  2621440
REGISTRATION_OPEN            False
DEFAULT_FROM_EMAIL           webmaster@g10f.de
STATIC_ROOT                  ../htdocs/static
MEDIA_ROOT                   ../htdocs/media
SSO_THEME                    None
ROOT_URLCONF                 sso.urls
===========================  =========================  =========================


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
