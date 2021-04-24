#!/bin/bash

cd embark
uwsgi --wsgi-file embark/wsgi.py  --http :8000 --workers=2