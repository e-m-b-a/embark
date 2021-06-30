#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings
pip install -r requirements.txt
python3 manage.py runapscheduler --test &
uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :8000 --processes 2 --threads 10 &
daphne embark.asgi:application -p 8001 -b '0.0.0.0'
