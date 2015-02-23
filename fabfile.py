from __future__ import with_statement
import posixpath

from fabric.api import *
from fabric.api import local, run, cd
from fabtools import require
import fabtools


env.use_ssh_config = True
env.apps = ['sso']

configurations = {
    'dev': {'host_string': 'sso.dwbn.org', 'server_name': 'sso-dev.dwbn.org', 'app': 'sso', 'virtualenv': 'sso-dev', 'db_name': 'sso_dev'},
    'prod': {'host_string': 'sso.dwbn.org', 'server_name': 'sso.dwbn.org', 'app': 'sso', 'virtualenv': 'sso', 'db_name': 'sso'},
    'g10f': {'host_string': 'g10f', 'server_name': 'sso.g10f.de', 'app': 'sso', 'virtualenv': 'sso', 'db_name': 'sso'},
    'elsapro': {'host_string': 'g10f', 'server_name': 'sso.elsapro.com', 'app': 'sso', 'virtualenv': 'sso', 'db_name': 'vw_sso'},
}

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
    listen 443 ssl default_server;
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
        add_header Strict-Transport-Security max-age=31536000;
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

REGISTRATION_TEMPLATE = """\
server {
    listen 80;
    server_name %(server_name)s;
    # path for static files
    root %(docroot)s;
    return 301 https://%(target_name)s/accounts/register/;
}
"""

NGINX_SSL_TEMPLATE = """\
#ssl                       on;
ssl_certificate           %(certroot)s/certificate.crt;
ssl_certificate_key       %(certroot)s/certificate.key;
ssl_dhparam               %(certroot)s/dh2048.pem;
ssl_session_cache         builtin:1000  shared:SSL:10m;
ssl_prefer_server_ciphers on;
add_header                Strict-Transport-Security "max-age=63072000;";
ssl_protocols             TLSv1 TLSv1.1 TLSv1.2;
"""

GUNICORN_TEMPLATE = """\
import multiprocessing
import os
bind = "unix:/tmp/%(server_name)s.gunicorn.sock"
workers = multiprocessing.cpu_count() + 2
pythonpath = '%(code_dir)s/src/apps'
errorlog = '%(code_dir)s/logs/gunicorn-error.log'
os.environ['DEBUG'] = ""
os.environ['THROTTELING_DISABLED'] = "False"
"""


@task
def compileless(version='1.0.11'):
    for style in ['default', 'dwbn', 'cerulean', 'slate', 'vw']:
        local('lessc ./apps/sso/static/less/%(style)s.less ./apps/sso/static/css/%(style)s-%(version)s.css' %{'style': style, 'version': version})


@task
def compilemessages():
    with lcd('apps'):
        local('~/envs/sso/bin/python manage.py compilemessages')


@task
def makemessages():
    with lcd('apps'):
        local('~/envs/sso/bin/python manage.py makemessages -a')


@task
def test():
    with lcd('apps'):	
        local("~/envs/sso/bin/python manage.py test streaming accounts oauth2")


@task
def prepare_deploy():
    compilemessages()
    #test()
    local("git commit -a")
    local("git push -u origin master")


def migrate_data(python, server_name, code_dir, app):
    sudo("%s ./src/apps/manage.py migrate" % python, user='www-data', group='www-data')
    # sudo("%s ./src/apps/manage.py loaddata l10n_data.xml" % python, user='www-data', group='www-data')


@task
def createsuperuser(conf='dev'):
    configuration = configurations.get(conf)
    server_name = configuration['server_name']
    virtualenv = configuration['virtualenv']
    code_dir = '/proj/%s' % server_name
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    with cd(code_dir):
        run("%s ./src/apps/manage.py createsuperuser --username=admin --email=admin@g10f.de" % python)
    

@task
def update_debian():
    sudo('apt-add-repository ppa:ubuntugis/ppa')  # add gis repository
    fabtools.deb.update_index()
    fabtools.deb.upgrade(safe=False)
    sudo('reboot')
    

def deploy_debian():
    require.deb.package('libpq-dev')
    require.deb.package('libjpeg62-dev')
    # Geospatial libraries
    require.deb.package('binutils')
    require.deb.package('libproj-dev')
    require.deb.package('gdal-bin')
    require.deb.package('postgresql-9.1-postgis-2.0')


def deploy_database(db_name):
    # Require a PostgreSQL server
    # require.postgres.server()
    require.postgres.user(db_name, db_name)
    require.postgres.database(db_name, db_name)
    fabtools.postgres._run_as_pg('''psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" %(db_name)s''' % {'db_name': db_name})
    fabtools.postgres._run_as_pg('''psql -c "ALTER TABLE spatial_ref_sys OWNER TO %(db_name)s;" %(db_name)s''' % {'db_name': db_name})


def deploy_webserver(code_dir, server_name):
    # Require an nginx server proxying to our app
    docroot = '/proj/static/htdocs/%(server_name)s' % {'server_name': server_name}    
    context = {'certroot': '/proj/g10f/certs', 'server_name': server_name, 'host_string': env.host_string, 'code_dir': code_dir}
    
    require.directory('%(code_dir)s/logs' % context, use_sudo=True, owner="www-data", mode='770')
    require.directory('%(code_dir)s/config' % context, use_sudo=True, owner="www-data", mode='770')
    require.directory(docroot, use_sudo=True, owner="www-data", mode='770')
    
    require.nginx.server()
    
    require.files.directory(context['certroot'], use_sudo=True, owner='www-data', group='www-data')
    require.files.template_file('/etc/nginx/conf.d/ssl.nginx.conf', template_contents=NGINX_SSL_TEMPLATE, context=context, use_sudo=True)
    require.file('%(certroot)s/certificate.crt' % context, source='certs/%(host_string)s.certificate.crt' % context, use_sudo=True, owner='www-data', group='www-data')
    require.file('%(certroot)s/certificate.key' % context, source='certs/%(host_string)s.certificate.key' % context, use_sudo=True, owner='www-data', group='www-data')
    require.file('%(certroot)s/dh2048.pem' % context, source='certs/%(host_string)s.dh2048.pem' % context, use_sudo=True, owner='www-data', group='www-data')
    require.files.template_file('%(code_dir)s/config/nginx.expired.conf' % context, template_contents=NGINX_EXPIRED_TEMPLATE, use_sudo=True, owner='www-data', group='www-data')
    require.files.template_file('%(code_dir)s/config/nginx.webfonts.conf' % context, template_contents=NGINX_WEBFONTS_TEMPLATE, use_sudo=True, owner='www-data', group='www-data')
    
    require.nginx.site(server_name, template_contents=PROXIED_SITE_TEMPLATE, docroot=docroot)
    
    if env.host_string in ['dwbn']:
        require.nginx.site('register.diamondway-buddhism.org', template_contents=REGISTRATION_TEMPLATE, docroot=docroot, target_name=server_name)
        

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
def deploy(conf='dev'):
    configuration = configurations.get(conf)
    server_name = configuration['server_name']
    app = configuration['app']
    virtualenv = configuration['virtualenv']
    db_name = configuration['db_name']
    env.host_string = configuration['host_string']
    
    code_dir = '/proj/%s' % server_name
    
    user = 'ubuntu'
    # setup_user(user)
    # require.files.directory(code_dir)
    # deploy_debian()
    # deploy_webserver(code_dir, server_name)
    # fabtools.user.modify(name=user, extra_groups=['www-data'])
    # deploy_database(db_name)

    with cd(code_dir):
        require.git.working_copy('git@bitbucket.org:dwbn/sso.git', path='src', branch='master')
        sudo("chown www-data:www-data -R  ./src")
        sudo("chmod g+w -R  ./src")
    
    # local settings 
    require.file('%(code_dir)s/src/apps/%(app)s/settings/local_settings.py' % {'code_dir': code_dir, 'app': app}, 
                 source='apps/%(app)s/settings/local_%(server_name)s.py' % {'server_name': server_name, 'app': app},
                 use_sudo=True, owner='www-data', group='www-data')

    """
    # python enviroment
    require.python.virtualenv('/envs/%s' % virtualenv)
    with fabtools.python.virtualenv('/envs/%s' % virtualenv):
        with cd(code_dir):
            require.python.requirements('src/requirements.txt')
    
    require.file('/envs/%(virtualenv)s/lib/python2.7/sitecustomize.py' % {'virtualenv': virtualenv}, source='apps/sitecustomize.py')
    
    # configure gunicorn
    require.directory('%(code_dir)s/config' % {'code_dir': code_dir}, use_sudo=True, owner="www-data", mode='770')
    config_filename = '%(code_dir)s/config/gunicorn_%(server_name)s.py' % {'code_dir': code_dir, 'server_name': server_name}
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
    """
    
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    with cd(code_dir):
        update_dir_settings(code_dir + '/logs')
        migrate_data(python, server_name, code_dir, app)
        sudo("supervisorctl restart %(server_name)s" % {'server_name': server_name})
        sudo("%s ./src/apps/manage.py collectstatic --noinput" % python)
        update_dir_settings(code_dir + '/logs')
