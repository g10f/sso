#!/usr/bin/env bash
set -exf


if [ "x$DJANGO_MIGRATE" = 'xon' ]; then
	./manage.py migrate --noinput
fi

if [ "x$DJANGO_CREATE_SUPERUSER" = 'xon' ]; then
    user_count=$(./manage.py user_count)
    if [ "$user_count" = 0 ]; then
      ./manage.py createsuperuser --noinput
    fi
fi

if [ "x$DJANGO_LOAD_INITIAL_DATA" = 'xon' ]; then
	./manage.py loaddata l10n_data app_roles roles browser_client_data
fi

# shellcheck disable=SC2068
exec $@
