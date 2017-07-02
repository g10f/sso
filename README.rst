SSO
========

*An identity provider with OpenID Connect support.*

Prepare a development environment
----------------------------------
1. get python >= 3.5
4. create virtualenv for sso:  ``python3 -m venv /venv/sso``
5. install sso requirements in the virtualenv with: ``pip install -r requirements.txt``
6. install postgresql
7. update template1 database for using citext extension in tests:  ``sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS citext;" template1`` (where -u postgres is your postgres user)
8. create the database with ``./manage.py syncdb``

Documentation
--------------


Changelog
----------

1.0.0: OAuth2 and OpenID Connect Support
1.1.0: JSONLD/Hydra Api 
1.2.0: Organisation Data Management
