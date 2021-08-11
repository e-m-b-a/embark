#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings
echo -e "[*] Starting migrations"
python3 manage.py makemigrations users uploader
python3 manage.py migrate
echo -e "[*] Starting runapscheduler"
python3 manage.py runapscheduler --test &
echo -e "[*] Starting uwsgi"
uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :80 --processes 2 --threads 10 &
echo -e "[*] Starting daphne"
# shellcheck disable=2094
daphne -v 3 --access-log ./logs/daphne.log embark.asgi:application -p 8001 -b '0.0.0.0' &> ./logs/daphne.log
