from __future__ import with_statement
import posixpath
from fabric.api import *
from fabric.api import local, settings, abort, run, cd
from fabric.contrib.console import confirm
from fabric.contrib import files
from fabric.colors import red
from fabtools import require
import fabtools

env.use_ssh_config = True
env.apps = ['sso']
# map valid  server names to enviroments, to ensure we deploy accurately
valid_server_names = {
    'g10f': ['dwbn-sso.g10f.de', 'sso.g10f.de', 'sso.elsapro.com'],
    'elsapro': ['sso.elsapro.com'],
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

NGINX_WEBFONTS_TEMPLATE = """\
location ~* \.(?:ttf|ttc|otf|eot|woff)$ {
    add_header "Access-Control-Allow-Origin" "*";
    expires 1M;
    access_log off;
    add_header Cache-Control "public";
}
"""

NGINX_EXPIRED_TEMPLATE = """\
# Media: images, icons, video, audio, HTC
location ~* \.(?:jpg|jpeg|gif|png|ico|cur|gz|svg|svgz|mp4|ogg|ogv|webm|htc)$ {
  expires 1M;
  access_log off;
  add_header Cache-Control "public";
}
# CSS and Javascript
location ~* \.(?:css|js)$ {
  expires 1y;
  access_log off;
  add_header Cache-Control "public";
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

    # Media: images, video, audio, HTC, WebFonts
    location /static {
        include /proj/%(server_name)s/config/nginx.expired.conf;
        include /proj/%(server_name)s/config/nginx.webfonts.conf;
    }
    location /media {
        include /proj/%(server_name)s/config/nginx.expired.conf;
    }

    location @proxied {
        add_header X-UA-Compatible IE=edge;
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

NGINX_SSL_TEMPLATE = """\
#ssl                       on;
ssl_certificate           %(certroot)s/certificate.crt;
ssl_certificate_key       %(certroot)s/certificate.key;
#ssl_ciphers               RC4:HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache         shared:SSL:10m;
"""

GUNICORN_TEMPLATE = """\
import multiprocessing
import os
bind = "unix:/tmp/%(server_name)s.gunicorn.sock"
workers = multiprocessing.cpu_count() + 2
pythonpath = '%(code_dir)s/src/apps'
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

@task 
def prepare_deploy():
    compilemessages()
    #test()
    local("git commit -a")
    local("git push -u origin master")

@task
def perms():
    django.manage.run(command="update_permissions")

def migrate_data(python, server_name, code_dir, app):
    sudo("%s ./src/apps/manage.py syncdb --noinput" % python, user='www-data', group='www-data')
    #sudo("%s ./src/apps/manage.py migrate accounts" % python, user='www-data', group='www-data')
    #sudo("%s ./src/apps/manage.py migrate registration 0001 --fake" % python, user='www-data', group='www-data')
    #sudo("%s ./src/apps/manage.py migrate registration" % python, user='www-data', group='www-data')
    

@task
def createsuperuser(server_name='', virtualenv='sso'): 
    server_name = check_server_name(server_name)
    code_dir = '/proj/%s' % server_name
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    with cd(code_dir):
        run("%s ./src/apps/manage.py createsuperuser --username=admin --email=admin@g10f.de" % python)
    
@task
def update_debian():
    fabtools.deb.update_index()
    fabtools.deb.upgrade(safe=False)
    sudo('reboot')
    
def deploy_debian():    
    require.deb.package('libpq-dev')
    require.deb.package('libmysqlclient-dev')
    require.deb.package('libjpeg62')
    require.deb.package('libjpeg62-dev')
    
def deploy_database(db_name):
    # Require a PostgreSQL server
    require.postgres.server()
    require.postgres.user(db_name, db_name)
    require.postgres.database(db_name, db_name)

def deploy_webserver(code_dir, server_name):
    # Require an nginx server proxying to our app
    docroot = '/proj/static/htdocs/%(server_name)s' % {'server_name': server_name}
    require.directory('%(code_dir)s/logs' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    require.directory('%(code_dir)s/config' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    require.directory(docroot, use_sudo=True, owner="www-data", mode='770')
    
    #require.nginx.server()
    
    #context = {'certroot': '/proj/g10f/certs', 'server_name': server_name}
    #require.files.directory(context['certroot'], use_sudo=True, owner='www-data', group='www-data')
    #require.files.template_file('/etc/nginx/conf.d/ssl.nginx.conf', template_contents=NGINX_SSL_TEMPLATE, context=context, use_sudo=True)
    #require.file('%(certroot)s/certificate.crt' % context, source='certs/%(server_name)s.certificate.crt' % context, use_sudo=True, owner='www-data', group='www-data')
    #require.file('%(certroot)s/certificate.key' % context, source='certs/%(server_name)s.certificate.key' % context, use_sudo=True, owner='www-data', group='www-data')
    require.files.template_file('%s/config/nginx.expired.conf' % code_dir, template_contents=NGINX_EXPIRED_TEMPLATE)
    require.files.template_file('%s/config/nginx.webfonts.conf' % code_dir, template_contents=NGINX_WEBFONTS_TEMPLATE)
    
    require.nginx.site(server_name, template_contents=PROXIED_SITE_TEMPLATE, docroot=docroot)

def deploy_app():
    pass
    
def setup_user(user):
    # add the id_rsa files for accessing the bitbucket repository 
    ssh_dir = posixpath.join(fabtools.user.home_directory(user), '.ssh')
    require.files.directory(ssh_dir, mode='700', owner=user, use_sudo=True)
    id_rsa = posixpath.join(ssh_dir, 'id_rsa')
    id_rsa_pub = posixpath.join(ssh_dir, 'id_rsa.pub')
    require.file(id_rsa, source='secret/id_rsa_ubuntu', mode='0600', owner=user, use_sudo=True)
    require.file(id_rsa_pub, source='secret/id_rsa_ubuntu.pub',  mode='0644', owner=user, use_sudo=True)
    
    require.files.directory('/proj', use_sudo=True, owner=user)
    require.files.directory('/envs', use_sudo=True, owner=user)    
    
def update_dir_settings(directory):
    sudo("chown www-data:www-data -R %s" % directory)  
    sudo("chmod 0660 -R %s" % directory)
    sudo("chmod +X %s" % directory)
    
@task 
def deploy(server_name='', app='sso', virtualenv='sso', db_name='sso'):
    server_name = check_server_name(server_name)
    code_dir = '/proj/%s' % server_name
    
    #user = 'ubuntu'
    #setup_user(user)
    require.files.directory(code_dir)
    #deploy_debian()
    deploy_webserver(code_dir, server_name)
    
    #fabtools.user.modify(name=user, extra_groups=['www-data'])
    #deploy_database(db_name)
    
    with cd(code_dir):
        require.git.working_copy('git@bitbucket.org:dwbn/sso.git', path='src')
        sudo("chown www-data:www-data -R  ./src")
        sudo("chmod g+w -R  ./src")
    
    # local settings 
    require.file('%(code_dir)s/src/apps/%(app)s/settings/local_settings.py' % {'code_dir': code_dir, 'app': app}, 
                 source='apps/%(app)s/settings/local_%(server_name)s.py' % {'server_name': server_name, 'app': app},
                 use_sudo=True, owner='www-data', group='www-data')

    """
    # python enviroment 
    require.python.virtualenv('/envs/sso')
    with fabtools.python.virtualenv('/envs/sso'):
        with cd(code_dir):
            require.python.requirements('src/requirements.txt')
    
    require.file('/envs/%(virtualenv)s/lib/python2.7/sitecustomize.py' % {'virtualenv': virtualenv}, source='apps/sitecustomize.py')
    """
    
    # configure gunicorn
    require.directory('%(code_dir)s/config' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    config_filename = '%(code_dir)s/config/gunicorn_%(server_name)s.conf' % {'code_dir': code_dir, 'server_name': server_name}
    context = {'server_name': server_name, 'code_dir': code_dir}
    require.files.template_file(config_filename, template_contents=GUNICORN_TEMPLATE, context=context, use_sudo=True)
    
    # Require a supervisor process for our app
    require.supervisor.process(
        server_name,
        command='/envs/%(virtualenv)s/bin/gunicorn -c %(config_filename)s %(app)s.wsgi:application' % {'virtualenv': virtualenv, 'config_filename': config_filename, 'app': app},
        directory=code_dir + '/src/apps',
        user='www-data'
        )
    
    # configure logrotate 
    config_filename = '/etc/logrotate.d/%(server_name)s' % {'server_name': server_name}
    context = {'code_dir': code_dir}
    require.files.template_file(config_filename, template_contents=LOGROTATE_TEMPLATE, context=context, use_sudo=True)
    
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    with cd(code_dir):
        update_dir_settings(code_dir + '/logs')
        #migrate_data(python, server_name, code_dir, app)
        sudo("%s ./src/apps/manage.py collectstatic --noinput" % python)
        sudo("supervisorctl restart %(server_name)s" % {'server_name': server_name})
        update_dir_settings(code_dir + '/logs')
    