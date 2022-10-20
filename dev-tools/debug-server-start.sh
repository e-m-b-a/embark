#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2022 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Automates setup of developer environment for Debug-Server

# RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
# BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color

PORT="8000"
IP="127.0.0.1"


export DJANGO_SETTINGS_MODULE=embark.settings.dev
export EMBARK_DEBUG=True
export PIPENV_VENV_IN_PROJECT="True"

cleaner() {
  if [[ -f ./embark/embark.log ]]; then
    rm ./embark/embark.log -f
  fi
  
  # killall -9 -q "*daphne*"
  docker container stop embark_db_dev
  docker container stop embark_redis_dev

  docker container prune -f --filter "label=flag"

  fuser -k "$PORT"/tcp
  exit 1
}

set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1
cd .. || exit 1

echo -e "\n$GREEN""$BOLD""Configuring Embark""$NC"

# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f ./docker-compose-dev.yml up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi

if ! [[ -d ./logs ]]; then
  mkdir ./logs
fi

# db_init
echo -e "[*] Starting migrations - log to embark/logs/migration.log"
pipenv run ./embark/manage.py makemigrations users uploader reporter dashboard | tee -a ./logs/migration.log
pipenv run ./embark/manage.py migrate | tee -a ./logs/migration.log

# superuser
pipenv run ./embark/manage.py createsuperuser --noinput

echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
docker container logs embark_redis_dev -f > ./logs/redis_dev.log &
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
docker container logs embark_db_dev -f > ./logs/mysql_dev.log & 

##
echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
pipenv run ./embark/manage.py runapscheduler | tee -a ./logs/scheduler.log &

# echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
# echo "START DAPHNE" >./logs/daphne.log
# cd ./embark || exit 1
# pipenv run daphne -v 3 -p 8001 -b "$IP" --root-path="$PWD"/embark embark.asgi:application &>../logs/daphne.log &
# cd .. || exit 1

# start embark
systemctl start embark.service
echo -e "$ORANGE""$BOLD""start EMBArk server (WS/WSS not enabled -a also asgi)""$NC"
pipenv run ./embark/manage.py runserver "$IP":"$PORT" |& tee -a ./logs/debug-server.log

wait

echo -e "\n$ORANGE""$BOLD""Done. To clean-up use the clean-setup script""$NC"