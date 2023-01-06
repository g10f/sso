#!/bin/bash
MANAGE="../venv/bin/python ../apps/manage.py"

function db() {
    ##############################################################
    # DB Migration
    # kubectl port-forward services/sso-db-postgresql 65432:5432
    # export PGPASSWORD=xxx
    sudo -u postgres psql -c 'DROP DATABASE IF EXISTS sso'
    sudo -u postgres psql -c 'CREATE DATABASE sso OWNER sso'
    export PGUSER=sso
    pg_dump -h localhost -p 65432 -d sso -F c > sso.dump
    sudo -u postgres pg_restore -h localhost -p 5432 -F c -d sso < sso.dump
}

function media() {
    ## start pod with rsync server and forward ssh and postgres port
    # kubectl apply -f rsync.yaml
    # kubectl port-forward pods/rsync 2222:2222
    ssh-keygen -f "/home/gunnar/.ssh/known_hosts" -R "[localhost]:2222"
    rsync -v -e 'ssh -o "StrictHostKeyChecking no" -p 2222' -az --delete localhost:/opt/g10f/sso/htdocs/media/organisation_image/ /home/gunnar/workspace/sso/htdocs/media/organisation_image/
    rsync -v -e 'ssh -o "StrictHostKeyChecking no" -p 2222' -az --delete localhost:/opt/g10f/sso/htdocs/media/image/ /home/gunnar/workspace/sso/htdocs/media/image/
    rm -r /home/gunnar/workspace/sso/htdocs/media/cache/
    $MANAGE thumbnail clear
    $MANAGE thumbnail cleanup
    $MANAGE migrate
}

# db
media
