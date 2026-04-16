#!/bin/sh
set -e

if [ "$1" = "web" ]; then
  python manage.py migrate --noinput
  python manage.py seed_initial_data
  python manage.py runserver 0.0.0.0:8000
elif [ "$1" = "worker" ]; then
  celery -A config worker -l info
elif [ "$1" = "beat" ]; then
  celery -A config beat -l info
else
  exec "$@"
fi
