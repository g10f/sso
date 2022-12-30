#!/usr/bin/env bash
set -ef


if [ "$DJANGO_MIGRATE" = "on" ]; then
	./manage.py migrate --noinput
fi

if  [ "$DJANGO_CREATE_SUPERUSER" = "on" ] || [ "$DJANGO_LOAD_INITIAL_DATA" = "on"  ]; then
  user_count=$(./manage.py user_count)

  if [[ $user_count -eq 0 ]]; then

    if  [ "$DJANGO_CREATE_SUPERUSER" = "on" ]; then
      ./manage.py createsuperuser --noinput
    fi

    if [ "$DJANGO_LOAD_INITIAL_DATA" = "on" ]; then
      ./manage.py loaddata l10n_data app_roles roles browser_client_data
    fi

  fi
fi

# shellcheck disable=SC2068
exec $@
