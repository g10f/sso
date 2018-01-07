SSO with OpenID Connect
=======================

*An identity provider with OpenID Connect support.*

Prepare a development environment
----------------------------------
#) get python >= 3.5
#) create virtualenv for sso:  ``python3 -m venv /venv/sso``
#) install sso requirements in the virtualenv with: ``pip install -r requirements.txt``
#) install postgresql
#) update template1 database for using citext extension in tests:  ``sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS citext;" template1`` (where -u postgres is your postgres user)
#) create the database with ``./manage.py migrate``

Documentation
--------------


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
