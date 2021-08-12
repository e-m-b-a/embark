#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings

if ! [[ -d logs ]]; then
  mkdir logs
fi

echo -e "[*] Starting migrations - log to ./logs/migration.log"
python3 manage.py makemigrations users uploader | tee -a ./logs/migration.log
python3 manage.py migrate | tee -a ./logs/migration.log
echo -e "[*] Starting runapscheduler"
python3 manage.py runapscheduler --test | tee -a ./logs/migration.log &
echo -e "[*] Starting uwsgi - log to ./logs/uwsgi.log"
uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :80 --processes 2 --threads 10 --logto ./logs/uwsgi.log &
echo -e "[*] Starting daphne - log to ./logs/daphne.log"
# shellcheck disable=2094
daphne -v 3 --access-log ./logs/daphne.log embark.asgi:application -p 8001 -b '0.0.0.0' &> ./logs/daphne.log
