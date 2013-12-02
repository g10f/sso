from __future__ import with_statement
from fabric.api import *
from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.contrib import files
from fabric.colors import red
from fabtools import require
import fabtools
#from termcolor import colored

#env.hosts = ['217.64.168.38']
env.use_ssh_config = True
env.apps = ['sso']
# map valid  server names to enviroments, to ensure we deploy accurately
valid_server_names = {
    'g10f': ['dwbn-sso.g10f.de', 'sso.g10f.de', 'sso2.g10f.de'],
    '54.246.101.129': ['sso.elsapro.com'],
    'dwbn001': ['sso.dwbn.org'],
}
    
def check_server_name(server_name):
    if (not server_name) and (len(env.hosts) == 1) and (env.hosts[0] in valid_server_names) and \
            (len(valid_server_names[env.hosts[0]]) == 1):
        server_name = valid_server_names[env.hosts[0]][0]
        return server_name
    else:
        for host in env.hosts:
            if not (server_name in valid_server_names[host]):
                print red('***********************************************')
                print red('Please check server name and host combination')
                print red('(%s, %s)' % (server_name, env.hosts))
                print red('Deployment was aborted.')
                print red('***********************************************')
                raise Exception("check_server_name failed")
        
        return server_name


LOGROTATE_TEMPLATE = """\
%(code_dir)s/logs/*.log {
    monthly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create
    sharedscripts
    postrotate
            [ ! -f /var/run/nginx.pid ] || kill -USR1 $(cat /var/run/nginx.pid)
            [ ! -f /var/run/supervisord.pid ] || kill -USR2 $(cat /var/run/supervisord.pid)
    endscript
}
"""

PROXIED_SITE_TEMPLATE = """\
upstream %(server_name)s.backend {
    server unix:/tmp/%(server_name)s.gunicorn.sock;
}
server {
    listen 80;
    server_name %(server_name)s;
    # path for static files
    root %(docroot)s;
    return 301 https://$server_name$request_uri;
}
server {
    listen 443 ssl;
    server_name %(server_name)s;

    # path for static files
    root %(docroot)s;

    try_files $uri @proxied;

    location @proxied {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_pass http://%(server_name)s.backend;
    }
    error_log                 /proj/%(server_name)s/logs/nginx-error.log error;
    access_log                /proj/%(server_name)s/logs/nginx-access.log;
}
"""

GUNICORN_TEMPLATE = """\
import multiprocessing
import os

bind = "unix:/tmp/%(server_name)s.gunicorn.sock"
workers = multiprocessing.cpu_count() + 2
pythonpath = '%(code_dir)s/apps'
errorlog = '%(code_dir)s/logs/gunicorn-error.log'
os.environ['DEBUG'] = ""
"""

    

@task
def compilemessages():
    for app in env.apps:
        with lcd('apps/%s' % app):
            local('django-admin.py compilemessages')

@task
def makemessages():
    for app in env.apps:
        with lcd('apps/%s' % app):
            local('django-admin.py makemessages -a ')

@task 
def test():
    with lcd('apps'):	
        local("~/envs/sso/bin/python ./manage.py test streaming accounts oauth2")

def commit():
    local("hg commit")

def push():
    local("hg push ssh://hg@bitbucket.org/GunnarScherf/sso")

@task 
def prepare_deploy():
    compilemessages()
    #test()
    commit()
    push()

def working_copy(code_dir):
    if not files.exists(code_dir):
        run("hg clone ssh://hg@bitbucket.org/GunnarScherf/sso %(code_dir)s" % {'code_dir': code_dir})
    else:
        with cd(code_dir):
            run("hg pull")
            run("hg update")
            sudo("chown www-data:www-data -R  ./apps")  


def migrate_data(python, new_db):
    run("%s ./apps/manage.py syncdb --noinput" % python)
    
    #run("%s ./apps/manage.py migrate accounts 0001 --fake" % python)
    run("%s ./apps/manage.py migrate accounts" % python)
    # after migrate accounts
    if new_db:
        run("%s ./apps/manage.py createsuperuser --username=admin --email=admin@g10f.de --noinput" % python)
    #run("%s ./apps/manage.py migrate oauth2" % python)
    
    #run("%s ./apps/manage.py migrate registration 0001 --fake" % python)
    #run("%s ./apps/manage.py migrate registration" % python)
        
    
@task 
def deploy(server_name='', app='sso', virtualenv='sso', db_name='sso'):
    server_name = check_server_name(server_name)
    
    code_dir = '/proj/%s' % server_name

    working_copy(code_dir)

    # local settings 
    require.file('%(code_dir)s/apps/%(app)s/settings/local_settings.py' % {'code_dir': code_dir, 'app': app}, 
                 source='apps/%(app)s/settings/local_%(server_name)s.py' % {'server_name': server_name, 'app': app})
    
    require.python.virtualenv('/envs/sso')
    return

    # python enviroment 
    with fabtools.python.virtualenv('/envs/sso'):
        require.python.package('sorl-thumbnail')
    require.file('/envs/%(virtualenv)s/lib/python2.7/sitecustomize.py' % {'virtualenv': virtualenv}, source='apps/sitecustomize.py')

    # Require a PostgreSQL server
    #require.postgres.server()
    new_db = False  # for createsueruser 
    new_db = not fabtools.postgres.database_exists(db_name)
    require.postgres.user(db_name, db_name)
    require.postgres.database(db_name, db_name)
    
    # configure gunicorn
    require.directory('%(code_dir)s/config' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    config_filename = '%(code_dir)s/config/gunicorn_%(server_name)s.conf' % {'code_dir': code_dir, 'server_name': server_name}
    context = {
        'server_name': server_name,
        'code_dir': code_dir,
    }
    require.files.template_file(config_filename, template_contents=GUNICORN_TEMPLATE, context=context, use_sudo=True)
    
    # Require a supervisor process for our app
    require.supervisor.process(
        server_name,
        command='/envs/%(virtualenv)s/bin/gunicorn -c %(config_filename)s %(app)s.wsgi:application' % {'virtualenv': virtualenv, 'config_filename': config_filename, 'app': app},
        directory=code_dir + '/apps',
        user='www-data'
        )
    
    # Require an nginx server proxying to our app
    """
    require.directory('%(code_dir)s/logs' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    require.nginx.site(
        server_name,
        template_contents=PROXIED_SITE_TEMPLATE,
        docroot='/proj/static/htdocs/%(server_name)s' % {'server_name': server_name},
        )
    
    # configure logrotate 
    config_filename = '/etc/logrotate.d/%(server_name)s' % {'server_name': server_name}
    context = {'code_dir': code_dir}
    require.files.template_file(config_filename, template_contents=LOGROTATE_TEMPLATE, context=context, use_sudo=True)
    """
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    
    with cd(code_dir):
        #migrate_data(python, new_db)
        run("%s ./apps/manage.py collectstatic --noinput" % python)
        sudo("chown www-data:www-data -R  ./logs")  
        sudo("chmod 770 -R  ./logs")  
        run("sudo supervisorctl restart %(server_name)s" % {'server_name': server_name})

@task
def perms():
    django.manage.run(command="update_permissions")
    