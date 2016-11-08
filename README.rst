SSO
========

*An identity provider with OpenID Connect support.*

Prepare a development environment
----------------------------------
1. get python >= 2.7
2. install pip package manager ( already installed if you're using Python 2 >=2.7.9 or Python 3 >=3.4 - https://pip.pypa.io/en/stable/installing/ - you might need tu update it via: ``` pip install -U pip ```)
3. install virtualenvwrapper: sudo pip install virtualenvwrapper
4. create virtualenv for sso:  mkvirtualenv sso
5. install sso requirements in the virtualenv with: pip install -r requirements.txt
6. install postgresql
7. update template1 database for using citext extension in tests:  sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS citext;" template1
8. create the database with ./manage.py syncdb


Deploy to AWS
--------------

1. launch ubuntu 12.04 LTS instance
2. associate domain i.e. sso.example.com to the instance
3. create ssl certificate files certificate.crt and certificate.key in sso/certs 
4. copy rsa private and public key files id_rsa_ubuntu and id_rsa_ubuntu.pub for bitbucket access into the folder sso/secret
5. run: fab -H sso.example.com update_debian
6. run: fab -H sso.example.com deploy:sso.example.com
7. run: fab -H sso.example.com createsuperuser:sso.example.com

Documentation
--------------


Changelog
----------

1.0.0: OAuth2 and OpenID Connect Support
1.1.0: JSONLD/Hydra Api 
1.2.0: Organisation Data Management

TODOs
-----------
1. User API 
1.1 check if organisation is correct when adding or changing users

Organisation:
Add Facebook, Twitter and Google URL