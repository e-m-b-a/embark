#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings
uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :8000 --workers=2 &
daphne embark.asgi:application -p 8001 -b '0.0.0.0'
