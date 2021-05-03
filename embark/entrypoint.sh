#!/bin/bash

uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :8000 --workers=2
hypercorn embark.asgi:application -b 127.0.0.1:8001
