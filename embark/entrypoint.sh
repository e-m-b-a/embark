#!/bin/bash

export DJANGO_SETTINGS_MODULE=embark.settings.docker
export EMBARK_DEBUG=True
export HTTP_PORT=80
export HTTPS_PORT=443
export BIND_IP='0.0.0.0'
export FILE_SIZE=2000000000

cd "$(dirname "$0")" || exit 1

# check emba
echo -e "$BLUE""$BOLD""checking EMBA""$NC"
# TODO pipe

# start venv (ignore source in script)
# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

# start the supervisor
systemctl enable embark.service
systemctl start embark.service

# !DIRECTORY-CHANGE!
cd /var/www/embark/ || exit 1

# logs
if ! [[ -d /var/www/logs ]]; then
  mkdir /var/www/logs
fi

# db_init
echo -e "\n[""$BLUE JOB""$NC""] Starting migrations - log to embark/logs/migration.log"
python3.10 manage.py makemigrations users uploader dashboard reporter | tee -a /var/www/logs/migration.log
python3.10 manage.py migrate | tee -a /var/www/logs/migration.log

# collect staticfiles and make accesable for server
echo -e "\n[""$BLUE JOB""$NC""] Collecting static files"
python3.10 manage.py collectstatic --no-input
chown www-embark /var/www/ -R
chmod 760 /var/www/media/ -R
# TODO other fileperms

echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
python3.10 manage.py runapscheduler | tee -a /var/www/logs/scheduler.log &
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting Apache"
python3.10 manage.py runmodwsgi --user www-embark --group sudo \
--host "$BIND_IP" --port="$HTTP_PORT" --limit-request-body "$FILE_SIZE" \
--url-alias /static/ /var/www/static/ \
--url-alias /media/ /var/www/media/ \
--allow-localhost --working-directory ./embark/ --server-root /var/www/httpd80/ \
--include-file /var/www/conf/embark.conf \
--server-name embark.local &
# --ssl-certificate /var/www/conf/cert/embark.local --ssl-certificate-key-file /var/www/conf/cert/embark.local.key \
# --https-port "$HTTPS_PORT" &
# --enable-debugger --https-only \
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
daphne --access-log /var/www/logs/daphne.log -e ssl:8000:privateKey=/var/www/conf/cert/embark-ws.local.key:certKey=/var/www/conf/cert/embark-ws.local.crt -b "$BIND_IP" -p 8001 -s embark-ws.local --root-path=/var/www/embark embark.asgi:application &
sleep 5

wait