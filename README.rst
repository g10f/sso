===
SSO
===
SSO is an OpenID Connect Identity Provider with user and organisation management.
The user and organisation data are exposed via a JSONLD/Hydra Api. Api entry point is /api/


Prepare a development environment
----------------------------------

#) Get python >= 3.5
#) Create virtualenv for sso:  ``python3 -m venv /venv/sso``
#) Activate the virtual environment ``source /venv/sso/bin/activate``
#) Update the Python package manager ``pip install -U pip``
#) Install sso requirements in the virtualenv with: ``pip install -r requirements.txt``
#) Install postgresql ``sudo apt install postgres``
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

1.0.0:
 OAuth2 and OpenID Connect Support

1.1.0:
 JSONLD/Hydra Api

1.2.0:
 Organisation Data Management

1.2.1:
 Django 2.0 compatibility
