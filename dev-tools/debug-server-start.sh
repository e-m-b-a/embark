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

PORT="8080"

cleaner() {
  fuser -k "$PORT"/tcp
  killall -9 -q "*daphne*"
  docker container stop embark_db_dev
  docker container stop embark_redis_dev
  docker network rm embark_dev
  docker container prune
  exit 1
}
set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1

# RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
# BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color

export DJANGO_SETTINGS_MODULE=embark.settings

echo -e "\n$GREEN""$BOLD""Configuring Embark""$NC"

cd .. || exit 1

# setup .env with dev network
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo -e "$ORANGE""$BOLD""Creating a Developer EMBArk configuration file .env""$NC"
export DATABASE_NAME="embark"
export DATABASE_USER="embark"
export DATABASE_PASSWORD="embark"
export DATABASE_HOST="127.0.0.1"
export DATABASE_PORT="3306"
export MYSQL_PASSWORD="embark"
export MYSQL_USER="embark"
export MYSQL_DATABASE="embark"
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="7777"
export SECRET_KEY="$DJANGO_SECRET_KEY"
# this is for pipenv/django # TODO change after 
{
  echo "DATABASE_NAME=$DATABASE_NAME"
  echo "DATABASE_USER=$DATABASE_USER" 
  echo "DATABASE_PASSWORD=$DATABASE_PASSWORD"
  echo "DATABASE_HOST=$DATABASE_HOST"
  echo "DATABASE_PORT=$DATABASE_PORT"
  echo "MYSQL_PASSWORD=$MYSQL_PASSWORD"
  echo "MYSQL_USER=$MYSQL_USER"
  echo "MYSQL_DATABASE=$MYSQL_DATABASE"
  echo "REDIS_HOST=$REDIS_HOST"
  echo "REDIS_PORT=$REDIS_PORT"
  echo "SECRET_KEY=$DJANGO_SECRET_KEY"
} > .env

# setup dbs-container and detach build could be skipt
echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
sudo docker-compose -f ./docker-compose-dev.yml build
DB_RETURN=$?
if [[ $DB_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
fi

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
sudo docker-compose -f ./docker-compose-dev.yml up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi

if ! [[ -d ./embark/logs ]]; then
  mkdir ./embark/logs
fi

# db_init
echo -e "[*] Starting migrations - log to embark/logs/migration.log"
pipenv run ./embark/manage.py makemigrations users uploader | tee -a ./embark/logs/migration.log
pipenv run ./embark/manage.py migrate | tee -a ./embark/logs/migration.log

echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
docker container logs embark_redis_dev -f > ./embark/logs/redis_dev.log &
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
docker container logs embark_db_dev -f > ./embark/logs/mysql_dev.log & 

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
pipenv run ./embark/manage.py runserver "$PORT"

wait %1
wait %2

#cleanup TODO stop and remove container and network


echo -e "\n$ORANGE""$BOLD""Done. To clean-up use the clean-setup script""$NC"