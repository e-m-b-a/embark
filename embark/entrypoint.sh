#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings
python3 manage.py makemigrations users uploader
python3 manage.py migrate
python3 manage.py runapscheduler --test &
uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :80 --processes 2 --threads 10 &
daphne -v 3 --access-log ./logs/daphne.log embark.asgi:application -p 8001 -b '0.0.0.0' &> ./logs/daphne.log
