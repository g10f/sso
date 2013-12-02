SSO
========

*A SSO Provider with OAuth2 support.*

Setup
-------
# see http://www.pip-installer.org/en/latest/installing.html
curl -O https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
sudo python ez_setup.py
curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python get-pip.py
sudo pip install virtualenvwrapper

# add this lines to .bashrc
# virtualenv
WORKON_HOME=/envs
PROJECT_HOME=/proj
source /usr/local/bin/virtualenvwrapper.sh
 

| # pip virtualenv and virtualenvwrapper
| sudo apt-get install python-distribute 
| curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
| sudo python get-pip.py

| sudo pip install virtualenv
| sudo pip install virtualenvwrapper
| mkvirtualenv sso
| pip install -r requirements.txt
| setvirtualenvproject /proj/sso
| sudo mkdir /proj/sso/logs
| sudo chown www-data:www-data /proj/sso


Documentation
--------------



Changelog
---------


1.0.0: OAuth2 and OpenID Support 
