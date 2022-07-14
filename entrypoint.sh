#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings.docker
export EMBARK_DEBUG=True
export HTTP_PORT=80
export HTTPS_PORT=443
export BIND_IP='0.0.0.0'
export FILE_SIZE=2000000000

# check emba
echo -e "$BLUE""$BOLD""checking EMBA""$NC"
# TODO

# start venv (ignore source in script)
# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

# dirs
if ! [[ -d /app/www/logs ]]; then
  mkdir /app/www/logs
fi

if ! [[ -d /app/www/conf ]]; then
  mkdir /app/www/conf
fi

#start the supervisor
systemctl enable embark.service
systemctl start embark.service

# copy django server
if [[ -d /app/www/embark ]]; then
  rm -R /app/www/embark
fi
cp -Ru ./embark/ /app/www/embark/

# config apache
# add all modules we want (mod_ssl mod_auth_basic etc)
# post_max_size increase
{
  echo ''
} > /app/www/conf/embark.conf

# !DIRECTORY-CHANGE!
cd /app/www/embark/ || exit 1

# db_init
echo -e "\n[""$BLUE JOB""$NC""] Starting migrations - log to embark/logs/migration.log"
pipenv run ./manage.py makemigrations users uploader dashboard reporter | tee -a /app/www/logs/migration.log
pipenv run ./manage.py migrate | tee -a /app/www/logs/migration.log

# collect staticfiles and make accesable for server
echo -e "\n[""$BLUE JOB""$NC""] Collecting static files"
pipenv run ./manage.py collectstatic --no-input
chown www-embark /app/www/ -R
# chown www-embark /app/emba -R
chmod 760 /app/www/media/ -R

echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
pipenv run ./manage.py runapscheduler | tee -a /app/www/logs/scheduler.log &
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting Apache"
pipenv run ./manage.py runmodwsgi --user www-embark --group sudo \
--host "$BIND_IP" --port="$HTTP_PORT" --limit-request-body "$FILE_SIZE" \
--url-alias /static/ /app/www/static/ \
--url-alias /media/ /app/www/media/ \
--allow-localhost --working-directory /app/www/embark/ --server-root /app/www/httpd80/ \
--include-file /app/www/conf/embark.conf \
--server-name embark.local \
--ssl-certificate /app/www/conf/cert/embark.local --ssl-certificate-key-file /app/www/conf/cert/embark.local.key \
--https-port "$HTTPS_PORT" &
# --enable-debugger --https-only \
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
pipenv run daphne --access-log /app/www/logs/daphne.log -e ssl:8000:privateKey=/app/www/conf/cert/embark-ws.local.key:certKey=/app/www/conf/cert/embark-ws.local.crt -b "$BIND_IP" -p 8001 -s embark-ws.local --root-path=/app/www/embark embark.asgi:application &
sleep 5


echo -e "\n""$ORANGE$BOLD""=============================================================""$NC"
echo -e "\n""$ORANGE$BOLD""Server started on http://embark.local""$NC"
echo -e "\n""$ORANGE$BOLD""For SSL you may use https://embark.local (Not recommended for local use)""$NC"
echo -e "\n\n""$GREEN$BOLD""the trusted rootCA.key for the ssl encryption is in /app/cert""$NC"
wait