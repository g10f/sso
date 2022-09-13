# certs for running runserver_plus with selfsigned cert for debugging fido
# requires django_extensions installed e.g. INSTALLED_APPS = INSTALLED_APPS + ['django_extensions']

runserver_plus --cert-file cert/cert.pem --key-file cert/key.pem  --keep-meta-shutdown
