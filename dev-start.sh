#!/bin/bash 

  # TODO make quiet no outputs
  export DJANGO_SETTINGS_MODULE=embark.settings

  if ! [[ -d embark/logs ]]; then
    mkdir embark/logs
  fi

  echo -e "[*] Setup logging of redis database - log to embark/logs/redis_db.log"
  docker container logs embark_redis_dev -f > ./embark/logs/redis_db.log &
  echo -e "[*] Setup logging of mysql database - log to embark/logs/mysql_db.log"
  docker container logs embark_db_dev -f > ./embark/logs/mysql_db.log &
  echo -e "[*] Starting migrations - log to embark/logs/migration.log"
  python3 ./embark/manage.py makemigrations users uploader | tee -a ./embark/logs/migration.log
  python3 ./embark/manage.py migrate | tee -a ./embark/logs/migration.log
  echo -e "[*] Starting runapscheduler"
  python3 ./embark/manage.py runapscheduler --test | tee -a ./embark/logs/migration.log &
  echo -e "[*] Starting uwsgi - log to /embark/logs/uwsgi.log"
  uwsgi --wsgi-file /app/embark/embark/wsgi.py --http :80 --processes 2 --threads 10 --logto ./embark/logs/uwsgi.log &
  echo -e "[*] Starting daphne - log to /embark/logs/daphne.log"
  # shellcheck disable=2094
  daphne -v 3 --access-log ./embark/logs/daphne.log embark.asgi:application -p 8001 -b '0.0.0.0' &> ./embark/logs/daphne.log