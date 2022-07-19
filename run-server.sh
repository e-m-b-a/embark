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
export FILE_SIZE=2000000000


cleaner() {
  pkill -u root daphne
  pkill -u root "$PWD"/emba/emba.sh
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
  systemctl disable embark.service
  exit 1
}

# main
set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1

if ! [[ $EUID -eq 0 ]] ; then
  echo -e "\\n$RED""Run Server script with root permissions!""$NC\\n"
  exit 1
fi

# check emba
echo -e "$BLUE""$BOLD""checking EMBA""$NC"
"$PWD"/emba/emba.sh -d
if [[ $? -eq 1 ]]; then
  echo -e "$BLUE""Trying auto-maintain""$NC"
  # automaintain
  if ! [[ -d ./emba ]]; then
    echo -e "$RED""EMBA not installed""$NC"
    exit 1
  fi
  cd ./emba || exit 1
  systemctl restart NetworkManager docker
  ./emba.sh -d 1>/dev/null
  if [[ $? -eq 1 ]]; then
    echo -e "$RED""EMBA is not configured correctly""$NC"
    exit 1
  fi
  cd .. || exit 1
fi

# check venv TODO
(cd /var/www && pipenv check)

# copy emba
cp -Ru ./emba/ /var/www/emba/

# Start container
echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f ./docker-compose.yml up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi

# logs
if ! [[ -d ./docker_logs ]]; then
  mkdir docker_logs
fi

# container-logs (2 jobs)
echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./docker_logs/redis.log" 
docker container logs embark_redis -f &> ./docker_logs/redis.log & 
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql.log"
docker container logs embark_db -f &> ./docker_logs/mysql.log &

# start the supervisor
systemctl enable embark.service
systemctl start embark.service

# copy django server
cp -R ./embark/ /var/www/embark/

# config apache
# add all modules we want (mod_ssl mod_auth_basic etc)
# post_max_size increase
if ! [[ -d /var/www/conf ]]; then
  mkdir /var/www/conf
fi
{
  echo -e ''
} > /var/www/conf/embark.conf

# certs
if ! [[ -d /var/www/conf/cert ]]; then
  mkdir /var/www/conf/cert
fi
cp -u "$PWD"/cert/embark.local /var/www/conf/cert
cp -u "$PWD"/cert/embark.local.key /var/www/conf/cert
cp -u "$PWD"/cert/embark-ws.local.key /var/www/conf/cert
cp -u "$PWD"/cert/embark-ws.local.crt /var/www/conf/cert
cp -u "$PWD"/cert/embark-ws.local /var/www/conf/cert

# cp .env
cp -u ./.env /var/www/embark/embark/settings/

# !DIRECTORY-CHANGE!
cd /var/www/embark/ || exit 1

# start venv (ignore source in script)
# shellcheck disable=SC1091
source /var/www/.venv/bin/activate || exit 1

# TODO move to parent
# logs
if ! [[ -d /var/www/logs ]]; then
  mkdir /var/www/logs
fi

# db_init
echo -e "\n[""$BLUE JOB""$NC""] Starting migrations - log to embark/logs/migration.log"
pipenv run ./manage.py makemigrations users uploader dashboard reporter | tee -a /var/www/logs/migration.log
pipenv run ./manage.py migrate | tee -a /var/www/logs/migration.log

# collect staticfiles and make accesable for server
echo -e "\n[""$BLUE JOB""$NC""] Collecting static files"
pipenv run ./manage.py collectstatic --no-input
chown www-embark /var/www/ -R
chmod 760 /var/www/media/ -R
# TODO other fileperms

echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
pipenv run ./manage.py runapscheduler | tee -a /var/www/logs/scheduler.log &
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting Apache"
pipenv run ./manage.py runmodwsgi --user www-embark --group sudo \
--host "$BIND_IP" --port="$HTTP_PORT" --limit-request-body "$FILE_SIZE" \
--url-alias /static/ /var/www/static/ \
--url-alias /media/ /var/www/media/ \
--allow-localhost --working-directory /var/www/embark/ --server-root /var/www/httpd80/ \
--include-file /var/www/conf/embark.conf \
--server-name embark.local --enable-debugger &
# --ssl-certificate /var/www/conf/cert/embark.local --ssl-certificate-key-file /var/www/conf/cert/embark.local.key \
# --https-port "$HTTPS_PORT" &
#  --https-only \
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
pipenv run daphne --access-log /var/www/logs/daphne.log -e ssl:8000:privateKey=/var/www/conf/cert/embark-ws.local.key:certKey=/var/www/conf/cert/embark-ws.local.crt -b "$BIND_IP" -p 8001 -s embark-ws.local --root-path=/var/www/embark embark.asgi:application &
sleep 5


echo -e "\n""$ORANGE$BOLD""=============================================================""$NC"
echo -e "\n""$ORANGE$BOLD""Server started on http://embark.local""$NC"
# echo -e "\n""$ORANGE$BOLD""For SSL you may use https://embark.local (Not recommended for local use)""$NC"
# echo -e "\n\n""$GREEN$BOLD""the trusted rootCA.key for the ssl encryption is in ./cert""$NC"
wait