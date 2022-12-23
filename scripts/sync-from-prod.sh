#!/bin/bash
MANAGE="../venv/bin/python ../apps/manage.py"

## start pod with rsync server and forward ssh and postgres port
# kubectl apply -f rsync.yaml
# kubectl port-forward pods/rsync 2222:2222
# kubectl port-forward services/sso-postgresql 65432:5432

## update local folder from production system
#ssh-keygen -f "/home/gunnar/.ssh/known_hosts" -R "[localhost]:2222"
#rsync -v -e 'ssh -o "StrictHostKeyChecking no" -p 2222' -az --delete localhost:/opt/g10f/sso/htdocs/media/organisation_image/ /home/gunnar/workspace/sso/htdocs/media/organisation_image/
#rsync -v -e 'ssh -o "StrictHostKeyChecking no" -p 2222' -az --delete localhost:/opt/g10f/sso/htdocs/media/image/ /home/gunnar/workspace/sso/htdocs/media/image/

## get sql data
#export PGPASSWORD=???
#pg_dump -h localhost -p 65432 -d sso -U sso | zip -q > sso.zip

sudo -u postgres psql -c "CREATE USER sso CREATEDB PASSWORD '$PGPASSWORD'"
sudo -u postgres psql -c 'DROP DATABASE IF EXISTS sso'
sudo -u postgres psql -c 'CREATE DATABASE sso OWNER sso'
unzip -p sso.zip | sudo -u postgres psql sso
rm -r /home/gunnar/workspace/sso/htdocs/media/cache/
$MANAGE thumbnail clear
$MANAGE thumbnail cleanup
$MANAGE migrate

psql -h localhost -p 65432 -d sso -U postgres
pg_dump -h sso-postgresql -d sso -U postgres | psql -h sso-db-postgresql -d sso -U postgres
pg_dump -h dev-postgresql -d sso_dev -U postgres | psql -h dev-db-postgresql -d sso_dev -U postgres
