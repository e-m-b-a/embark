#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2021 Siemens Energy AG
# Copyright 2020-2021 Siemens AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Starts the EMBArk on host

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

export DJANGO_SETTINGS_MODULE=embark.settings.deploy
export EMBARK_DEBUG=True
export HTTP_PORT=80
export HTTPS_PORT=443
export BIND_IP='0.0.0.0'
export FILE_SIZE=262144000  #250MB


cleaner() {
  pkill -u root daphne
  pkill -u root /app/emba/emba.sh
  pkill -u root runapscheduler

  fuser -k "$HTTP_PORT"/tcp
  fuser -k "$HTTPS_PORT"/tcp
  fuser -k 8000/tcp
  fuser -k 8001/tcp

  docker container stop embark_db
  docker container stop embark_redis
  docker network rm embark_backend
  docker container prune -f --filter "label=flag"

  systemctl stop embark.service
  exit 1
}

# main
set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1

if ! [[ $EUID -eq 0 ]] ; then
  echo -e "\\n$RED""Run EMBArk installation script with root permissions!""$NC\\n"
  exit 1
fi

# check emba
echo -e "$BLUE""$BOLD""checking EMBA""$RED"
/app/emba/emba.sh -d
if [[ $? -eq 1 ]]; then
  echo -e "$BLUE""Trying auto-maintain""$NC"
  # automaintain
  if ! [[ -d ./emba ]]; then
    echo -e "$RED""EMBA not installed""$NC"
    exit 1
  fi
  cd ./emba || exit 1
  git pull
  systemctl restart embark
  /app/emba/emba.sh -d 1>/dev/null
  if [[ $? -eq 1 ]]; then
    echo -e "$RED""EMBA is not configured correctly""$NC"
    exit 1
  fi
  cd .. || exit 1
fi

# start venv (ignore source in script)
# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

# Start container
echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f ./docker-compose.yml up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi

if ! [[ -d /app/www/logs ]]; then
  mkdir /app/www/logs
fi

if ! [[ -d /app/www/conf ]]; then
  mkdir /app/www/conf
fi

# container-logs (2 jobs)
echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log" 
docker container logs embark_redis -f &> /app/www/logs/redis.log & 
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log"
docker container logs embark_db -f &> /app/www/logs/mysql.log &

#start the supervisor
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