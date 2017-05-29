from __future__ import with_statement
import posixpath

from fabric.api import *
from fabric.contrib import files
import fabtools

try:
    from local_fabconfig import configurations
except:
    configurations = {
        'g10f': {'host_string': 'g10f', 'server_name': 'sso.g10f.de', 'app': 'sso', 'virtualenv': 'sso',
                 'db_name': 'sso', 'branch': 'master', 'bind': "127.0.0.1:8080", 'server': '127.0.0.1:6081'},
    }

env.use_ssh_config = True
env.apps = ['sso', 'password']
# env.msg_source_apps['sso']

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

HTTP_PROXIED_SITE_TEMPLATE = """\
# limit_req_zone $binary_remote_addr zone=sso:10m rate=1r/s;
upstream %(server_name)s.backend {
    server %(server)s;
}
server {
    listen 80;
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
        # limit_req zone=sso burst=10 nodelay;
        add_header X-UA-Compatible IE=edge;
        add_header Strict-Transport-Security max-age=31536000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_pass http://%(server_name)s.backend;
    }
    location ~ ^/robots.txt$ {alias /proj/static/htdocs/%(server_name)s/static/txt/robots.txt; }
    location ~ ^/favicon.ico$ {alias /proj/static/htdocs/%(server_name)s/static/ico/favicon.ico; }

    error_log                 /proj/%(server_name)s/logs/nginx-error.log error;
    access_log                /proj/%(server_name)s/logs/nginx-access.log;
}
"""

HTTP2_PROXIED_SITE_TEMPLATE = """\
upstream %(server_name)s.backend {
    server %(server)s;
}
server {
    listen [::]:80;
    listen      80;
    server_name %(server_name)s;
    # path for static files
    root %(docroot)s;
    return 301 https://%(server_name)s$request_uri;
}
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    # listen 443 ssl default_server;
    server_name %(server_name)s;
    add_header Strict-Transport-Security max-age=31536000;
    ssl_certificate /etc/letsencrypt/live/%(cert)s/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/%(cert)s/privkey.pem;
    ssl_dhparam /etc/nginx/dhparam.pem;

    # path for static files
    root %(docroot)s;

    try_files $uri @proxied;
    
    # required for certbot 
    location /.well-known/acme-challenge/ {
        alias /proj/static/htdocs/.well-known/acme-challenge/;
    }
    
    # Media: images, video, audio, HTC, WebFonts
    location /static {
        include %(code_dir)s/config/nginx.expired.conf;
        include %(code_dir)s/config/nginx.webfonts.conf;
    }
    location /media {
        include %(code_dir)s/config/nginx.expired.conf;
    }

    location @proxied {
        # limit_req zone=sso burst=10 nodelay;
        add_header X-UA-Compatible IE=edge;
        add_header Strict-Transport-Security max-age=31536000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_redirect off;
        proxy_pass http://%(server_name)s.backend;
    }
    location ~ ^/robots.txt$ {alias /proj/static/htdocs/%(server_name)s/static/txt/robots.txt; }
    location ~ ^/favicon.ico$ {alias /proj/static/htdocs/%(server_name)s/static/ico/favicon.ico; }

    error_log                %(code_dir)s/logs/nginx-error.log error;
    access_log               %(code_dir)s/logs/nginx-access.log;
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
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# Diffie-Hellman parameter for DHE ciphersuites, recommended 2048 bits
ssl_dhparam /etc/nginx/dhparam.pem;

# intermediate configuration. tweak to your needs.
# ssl_protocols TLSv1 TLSv1.1 TLSv1.2; # already in nginx.conf
ssl_ciphers 'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS';
# ssl_prefer_server_ciphers on; # already in nginx.conf

# HSTS (ngx_http_headers_module is required) (15768000 seconds = 6 months)
add_header Strict-Transport-Security max-age=15768000;

# OCSP Stapling ---
# fetch OCSP records from URL in ssl_certificate and cache them
ssl_stapling on;
ssl_stapling_verify on;

resolver 8.8.8.8;
"""

GUNICORN_TEMPLATE = """\
import multiprocessing
import os
bind = "%(bind)s"
workers = multiprocessing.cpu_count() + 2
pythonpath = '%(code_dir)s/src/apps'
errorlog = '%(code_dir)s/logs/gunicorn-error.log'
os.environ['DEBUG'] = ""
os.environ['THROTTELING_DISABLED'] = "False"
"""

RENEW_CERT_SCRIPT = """\
#!/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
letsencrypt renew --webroot -w /proj/static/htdocs
"""


@task
def compileless(version='1.0.19'):
    local('lessc ./apps/sso/static/less/default.less ./apps/sso/static/css/%(style)s-%(version)s.css' % {
        'style': 'default', 'version': version})


@task
def compilemessages():
    for app in env.apps:
        with lcd('apps/%s' % app):
            local('~/envs/sso/bin/django-admin.py compilemessages')


@task
def makemessages():
    for app in env.apps:
        with lcd('apps/%s' % app):
            local('~/envs/sso/bin/django-admin.py makemessages -a')
            local('~/envs/sso/bin/django-admin.py makemessages -d djangojs -a')


@task
def test():
    with lcd('apps'):
        local("~/envs/sso/bin/python manage.py test streaming accounts oauth2")


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
def deploy_debian(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']

    fabtools.require.deb.package('libjpeg-dev')
    fabtools.require.deb.package('zlib1g-dev')
    fabtools.require.deb.package('libtiff-dev')
    fabtools.require.deb.package('libfreetype6-dev')
    fabtools.require.deb.package('liblcms2-dev')
    fabtools.require.deb.package('libwebp-dev')
    fabtools.require.deb.package('libffi-dev')
    fabtools.require.deb.package('python-tk')
    fabtools.require.deb.package('tcl-dev')
    fabtools.require.deb.package('tk-dev')
    # postgres
    fabtools.require.deb.package('python3-dev')
    fabtools.require.deb.package('python-dev')
    fabtools.require.deb.package('libpq-dev')

    fabtools.require.deb.package('memcached')
    fabtools.require.deb.package('gcc')
    fabtools.require.deb.package('git')
    fabtools.require.deb.package('zip')
    fabtools.require.deb.package('unzip')

    # for letsencrypt
    fabtools.require.deb.package('letsencrypt')

    # postfix
    fabtools.require.deb.package("mailutils")
    # http://docs.aws.amazon.com/ses/latest/DeveloperGuide/postfix.html

    # python3-software-properties

    # required for python-u2flib-server
    fabtools.require.deb.package('swig')


@task
def deploy_database(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    db_name = configuration['db_name']

    # Require a PostgreSQL server
    fabtools.require.postgres.server()
    fabtools.require.deb.package('postgis')
    fabtools.require.deb.package('postgresql-contrib')  # for citext
    # for creating database  required (https://github.com/saz/puppet-locales/issues/28)
    fabtools.require.deb.package('language-pack-en')
    fabtools.require.postgres.user(db_name, db_name)
    fabtools.require.postgres.database(db_name, db_name)
    fabtools.postgres._run_as_pg(
        '''psql -c "CREATE EXTENSION IF NOT EXISTS citext;" %(db_name)s''' % {'db_name': db_name})
    fabtools.postgres._run_as_pg(
        '''psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" %(db_name)s''' % {'db_name': db_name})
    fabtools.postgres._run_as_pg(
        '''psql -c "ALTER TABLE spatial_ref_sys OWNER TO %(db_name)s;" %(db_name)s''' % {'db_name': db_name})
    # on development maschine create the extensions in the template1 for new test databases
    # sudo -u postgres psql -d template1 -c 'create extension citext;'
    # sudo -u postgres psql -d template1 -c 'create extension postgis;'

def table_is_empty(db_name, name):
    """
    Check if a name table is empty.
    """
    with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
        res = fabtools.postgres._run_as_pg('''psql -d %(db_name)s -t -A -c "SELECT COUNT(*) FROM %(name)s;"''' %
                                           {'db_name': db_name, 'name': name})
    return res == "0"


def update_timezones(db_name):
    with cd('~postgres'):
        fabtools.require.curl.command()
        with hide('stdout'):
            sudo('curl --silent -O http://efele.net/maps/tz/world/tz_world.zip', user='postgres')
        sudo('unzip tz_world.zip', user='postgres')
        with cd('world'):
            # create sql file
            sudo('shp2pgsql -S -a -s 4326 -I tz_world > tz_world.sql', user='postgres')
            # empty timezone table
            sudo('''psql -d %(db_name)s -c "TRUNCATE table tz_world; DROP INDEX IF EXISTS tz_world_geom_gist;"''' % {
                'db_name': db_name}, user='postgres')
            # load sql script
            with hide('stdout'):
                sudo('''psql -d %(db_name)s -f tz_world.sql''' % {'db_name': db_name}, user='postgres')
            sudo('''psql -c "ALTER TABLE tz_world OWNER TO %(db_name)s;" %(db_name)s''' % {'db_name': db_name},
                 user='postgres')

            # sudo('rm -R tz_world.zip')
            # sudo('rm -R world')


@task
def deploy_webserver(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    server_name = configuration['server_name']
    code_dir = '/proj/%s' % server_name
    ssl = configuration.get('ssl', configuration.get('ssl', True))
    server = configuration.get('server', configuration.get('bind', "unix:/tmp/%s.gunicorn.sock" % server_name))

    fabtools.require.nginx.server()
    if ssl and not files.exists('/etc/nginx/dhparam.pem', use_sudo=True):
        sudo('openssl dhparam -out /etc/nginx/dhparam.pem 2048')

    # Require an nginx server proxying to our app
    docroot = '/proj/static/htdocs/%(server_name)s' % {'server_name': server_name}
    context = {'server_name': server_name, 'host_string': env.host_string, 'code_dir': code_dir}

    fabtools.require.directory('%(code_dir)s/logs' % context, use_sudo=True, owner="www-data", mode='770')
    fabtools.require.directory('%(code_dir)s/config' % context, use_sudo=True, owner="www-data", mode='770')
    fabtools.require.directory(docroot, use_sudo=True, owner="www-data", mode='770')

    fabtools.require.files.template_file('%(code_dir)s/config/nginx.expired.conf' % context,
                                         template_contents=NGINX_EXPIRED_TEMPLATE, use_sudo=True, owner='www-data',
                                         group='www-data')
    fabtools.require.files.template_file('%(code_dir)s/config/nginx.webfonts.conf' % context,
                                         template_contents=NGINX_WEBFONTS_TEMPLATE, use_sudo=True, owner='www-data',
                                         group='www-data')

    if ssl:
        fabtools.require.files.template_file('/etc/nginx/conf.d/ssl.nginx.conf', template_contents=NGINX_SSL_TEMPLATE,
                                             context=context, use_sudo=True)

        fabtools.require.nginx.site(server_name, template_contents=HTTP2_PROXIED_SITE_TEMPLATE, docroot=docroot,
                                    code_dir=code_dir, cert=server_name, server=server)
    else:
        fabtools.require.nginx.site(server_name, template_contents=HTTP_PROXIED_SITE_TEMPLATE, docroot=docroot,
                                    code_dir=code_dir, cert=server_name, server=server)

    # if env.host_string in ['dwbn']:
    #    fabtools.require.nginx.site('register.diamondway-buddhism.org', template_contents=REGISTRATION_TEMPLATE,
    #                                docroot=docroot, target_name=server_name)


@task
def deploy_letsencrypt(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    server_name = configuration['server_name']

    fabtools.require.deb.package('letsencrypt')

    # sudo("service nginx stop")
    # sudo("letsencrypt certonly --standalone -d '%(server_name)s' -d 'www.%(server_name)s' -m mail@g10f.de -n" % {'server_name': server_name})
    # sudo("service nginx start")
    # sudo letsencrypt certonly --manual -d sso.dwbn.org

    # cron job for renew-certs
    fabtools.require.files.directory('/proj/scripts')
    renew_script = '/proj/scripts/renew-certs'
    fabtools.require.file(renew_script, RENEW_CERT_SCRIPT, mode='775')
    fabtools.cron.add_daily('renew-certs', 'root', "%s" % renew_script)


def setup_user(user):
    # add the id_rsa files for accessing the bitbucket repository 
    ssh_dir = posixpath.join(fabtools.user.home_directory(user), '.ssh')
    fabtools.require.files.directory(ssh_dir, mode='700', owner=user, use_sudo=True)
    id_rsa = posixpath.join(ssh_dir, 'id_rsa')
    id_rsa_pub = posixpath.join(ssh_dir, 'id_rsa.pub')
    fabtools.require.file(id_rsa, source='secret/id_rsa_ubuntu', mode='0600', owner=user, use_sudo=True)
    fabtools.require.file(id_rsa_pub, source='secret/id_rsa_ubuntu.pub', mode='0644', owner=user, use_sudo=True)

    fabtools.require.files.directory('/proj', use_sudo=True, owner=user)
    fabtools.require.files.directory('/envs', use_sudo=True, owner=user)


def update_dir_settings(directory):
    sudo("chown www-data:www-data -R %s" % directory)
    sudo("chmod 0660 -R %s" % directory)
    sudo("chmod +X %s" % directory)


@task
def activate_expiration(center_id, conf='dev'):
    configuration = configurations.get(conf)
    server_name = configuration['server_name']
    virtualenv = configuration['virtualenv']
    code_dir = '/proj/%s' % server_name
    env.host_string = configuration['host_string']
    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}

    with cd(code_dir):
        run("%(python)s ./src/apps/manage.py dwbn_activate_expiration %(center_id)s" % {'python': python,
                                                                                        'center_id': center_id})


@task
def prepare_deploy():
    compilemessages()
    # test()
    local("git commit -a")
    local("git push -u origin")


@task
def deploy_supervisor(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    server_name = configuration['server_name']
    virtualenv = configuration['virtualenv']
    app = configuration['app']
    code_dir = '/proj/%s' % server_name

    # configure gunicorn
    bind = configuration.get('bind', "unix:/tmp/%s.gunicorn.sock" % server_name)
    fabtools.require.directory('%(code_dir)s/config' % {'code_dir': code_dir}, use_sudo=True, owner="www-data",
                               group='www-data')
    config_filename = '%(code_dir)s/config/gunicorn_%(server_name)s.py' % {'code_dir': code_dir,
                                                                           'server_name': server_name}
    context = {'bind': bind, 'code_dir': code_dir}
    fabtools.require.files.template_file(config_filename, template_contents=GUNICORN_TEMPLATE, context=context,
                                         use_sudo=True)

    # Require a supervisor process for our app
    fabtools.require.supervisor.process(
        server_name,
        command='/envs/%(virtualenv)s/bin/gunicorn -c %(config_filename)s %(app)s.wsgi:application' % {
            'virtualenv': virtualenv, 'config_filename': config_filename, 'app': app},
        directory=code_dir + '/src/apps',
        user='www-data'
    )

    # Require a supervisor process for celery
    # https://github.com/celery/celery/blob/3.1/extra/supervisord/celeryd.conf
    logfile = code_dir + '/logs/celery-worker.log'
    fabtools.require.supervisor.process(
        'celery-%s' % server_name,
        command='/envs/%(virtualenv)s/bin/celery worker -A %(app)s -c 1 -l INFO -f %(logfile)s '
                '--without-gossip --without-mingle --without-heartbeat' %
                {'virtualenv': virtualenv, 'app': app, 'logfile': logfile},
        directory=code_dir + '/src/apps',
        user='www-data',
        numprocs=1,
        killasgroup=True,
        priority=1000
    )


@task
def deploy_app(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    server_name = configuration['server_name']
    app = configuration['app']
    virtualenv = configuration['virtualenv']
    user = configuration.get('user', 'ubuntu')

    code_dir = '/proj/%s' % server_name
    fabtools.require.files.directory(code_dir, use_sudo=True, owner='www-data', group='www-data')
    fabtools.require.files.directory('/envs', use_sudo=True, owner=user, group=user)

    with cd(code_dir):
        branch = configuration.get('branch', 'master')
        fabtools.require.git.working_copy('https://bitbucket.org/g10f/sso.git', path='src', branch=branch)
        sudo("chgrp www-data -R  ./src")
        sudo("chmod g+w -R  ./src")

    # local settings
    fabtools.require.file(
        '%(code_dir)s/src/apps/%(app)s/settings/local_settings.py' % {'code_dir': code_dir, 'app': app},
        source='apps/%(app)s/settings/local_%(server_name)s.py' % {'server_name': server_name, 'app': app},
        use_sudo=True, owner='www-data', group='www-data')

    # python enviroment
    # fabtools.require.python.virtualenv('/envs/%s' % virtualenv)
    # with fabtools.python.virtualenv('/envs/%s' % virtualenv):
    #     with cd(code_dir):
    #         fabtools.require.python.requirements('src/requirements.txt')


@task
def deploy(conf='dev'):
    configuration = configurations.get(conf)
    env.host_string = configuration['host_string']
    server_name = configuration['server_name']
    app = configuration['app']
    virtualenv = configuration['virtualenv']
    db_name = configuration['db_name']
    user = configuration.get('user', 'ubuntu')

    code_dir = '/proj/%s' % server_name

    fabtools.require.files.directory(code_dir)

    # setup_user(user)
    # fabtools.user.modify(name=user, extra_groups=['www-data'])

    # deploy_debian(conf)
    # deploy_database(conf)
    # deploy_letsencrypt(conf)
    # deploy_webserver(conf)
    deploy_app(conf)
    # deploy_supervisor(conf)

    # configure logrotate 
    config_filename = '/etc/logrotate.d/%(server_name)s' % {'server_name': server_name}
    context = {'code_dir': code_dir}
    fabtools.require.files.template_file(config_filename, template_contents=LOGROTATE_TEMPLATE, context=context,
                                         use_sudo=True)

    python = '/envs/%(virtualenv)s/bin/python' % {'virtualenv': virtualenv}
    with cd(code_dir):
        fabtools.require.files.directory(code_dir + '/logs')
        update_dir_settings(code_dir + '/logs')
        migrate_data(python, server_name, code_dir, app)
        sudo("supervisorctl restart %(server_name)s" % {'server_name': server_name})
        sudo("supervisorctl restart %(server_name)s" % {'server_name': 'celery-%s' % server_name, })
        sudo("%s ./src/apps/manage.py collectstatic --noinput" % python)
        update_dir_settings(code_dir + '/logs')

    if table_is_empty(db_name, 'tz_world'):
        update_timezones(db_name)
