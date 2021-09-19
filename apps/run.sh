#!/usr/bin/env bash

python manage.py migrate

user_count=$(python manage.py user_count)

if [[ $user_count = "0" ]]; then
  python manage.py loaddata l10n_data app_roles roles test_organisation_data
  python manage.py createsuperuser --noinput
fi

python manage.py runserver 0.0.0.0:8000
