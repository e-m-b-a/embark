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
    chmod 755 ./embark/embark.log
  fi
  fuser -k "$PORT"/tcp
  killall -9 -q "*daphne*"
  docker container stop embark_db_dev
  docker container stop embark_redis_dev
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
pipenv run ./embark/manage.py makemigrations users uploader | tee -a ./logs/migration.log
pipenv run ./embark/manage.py migrate | tee -a ./logs/migration.log

echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
docker container logs embark_redis_dev -f > ./logs/redis_dev.log &
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
docker container logs embark_db_dev -f > ./logs/mysql_dev.log & 

# run middlewears
# echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
# pipenv run ./embark/manage.py runapscheduler --test | tee -a ./embark/logs/migration.log &
# echo -e "\n[""$BLUE JOB""$NC""] Starting uwsgi - log to /embark/logs/uwsgi.log"
# pipenv run uwsgi --wsgi-file ./embark/embark/wsgi.py --http :80 --processes 2 --threads 10 --logto ./embark/logs/uwsgi.log &
# echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
# echo "START DAPHNE" >./embark/logs/daphne.log
# pipenv run daphne -v 3 -p 8001 -b 0.0.0.0 --root-path="$PWD"/embark embark.asgi:application &>>./embark/logs/daphne.log &

# start embark
echo -e "$ORANGE""$BOLD""start EMBArk server""$NC"
pipenv run ./embark/manage.py runserver "$IP":"$PORT"

wait %1
wait %2

echo -e "\n$ORANGE""$BOLD""Done. To clean-up use the clean-setup script""$NC"