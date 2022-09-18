#!/usr/bin/env bash
set -exf

[[ $(hostname) =~ -([0-9]+)$ ]] || exit 1
ordinal=${BASH_REMATCH[1]}

if [[ $ordinal -eq 0 ]];  then
  # only initialize if this is a pod ending with -0
  echo "Starting initialisation"

  if [[ x$DJANGO_MIGRATE = xon ]]; then
    ./manage.py migrate --noinput
  fi

  if  [[ x$DJANGO_CREATE_SUPERUSER = xon ]] || [[ x$DJANGO_LOAD_INITIAL_DATA = xon  ]]; then
      user_count=$(./manage.py user_count)

      if [[ $user_count = 0  ]]; then

        if  [[ x$DJANGO_CREATE_SUPERUSER = xon ]]; then
          ./manage.py createsuperuser --noinput
        fi

        if [[ x$DJANGO_LOAD_INITIAL_DATA = xon ]]; then
          ./manage.py loaddata l10n_data app_roles roles browser_client_data
        fi

      fi
  fi
fi

# shellcheck disable=SC2068
exec $@
