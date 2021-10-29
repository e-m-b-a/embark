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

# Description: Automates setup of developer enviroment

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color

export DJANGO_SETTINGS_MODULE=embark.settings

echo -e "\n$GREEN""$BOLD""Configuring Embark""$NC"


# setup .env with dev network
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
echo -e "$ORANGE""$BOLD""Creating a Developer EMBArk configuration file .env""$NC"
{
  echo "DATABASE_NAME=embark"
  echo "DATABASE_USER=root" 
  echo "DATABASE_PASSWORD=embark"
  echo "DATABASE_HOST=127.0.0.1"
  echo "DATABASE_PORT=3306"
  echo "MYSQL_ROOT_PASSWORD=embark"
  echo "MYSQL_DATABASE=embark"
  echo "REDIS_HOST=127.0.0.1"
  echo "REDIS_PORT=7777"
  echo "SECRET_KEY=$DJANGO_SECRET_KEY"
} > .env

# setup dbs-container and detach build could be skipt
  echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
docker-compose -f docker-compose-dev.yml build
DB_RETURN=$?
if [[ $DB_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
fi

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f docker-compose-dev.yml up -d
DU_RETURN=$?
if [[ $DU_RETURN -eq 0 ]] ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
fi

cd ./embark || exit 1
if ! [[ -d logs ]]; then
  mkdir logs
fi

# db_init
echo -e "[*] Starting migrations - log to embark/logs/migration.log"
pipenv run ./manage.py makemigrations users uploader | tee -a ./logs/migration.log
pipenv run ./manage.py migrate | tee -a ./logs/migration.log

# start embark
echo -e "$ORANGE""$BOLD""start embark server""$NC"
pipenv run ./manage.py runserver 



# echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
# docker container logs embark_redis_dev -f > ./embark/logs/redis_dev.log & # TODO test if this is quiet???
# echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
# docker container logs embark_db_dev -f > ./embark/logs/mysql_dev.log & 



# run middlewears
# echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
# pipenv run ./embark/manage.py runapscheduler --test | tee -a ./embark/logs/migration.log &
# echo -e "\n[""$BLUE JOB""$NC""] Starting uwsgi - log to /embark/logs/uwsgi.log"
# pipenv run uwsgi --wsgi-file ./embark/embark/wsgi.py --http :80 --processes 2 --threads 10 --logto ./embark/logs/uwsgi.log &
# echo -e "\n[""$BLUE JOB""$NC""] Starting daphne - log to /embark/logs/daphne.log"
# pipenv run daphne -v 3 --access-log ./embark/logs/daphne.log embark.asgi:application -p 8001 -b '0.0.0.0' &> ./embark/logs/daphne.log

# TODO cleanup
# if TODO ping -c 1 -I embark_dev -W 1 embark_db_dev; then
#  echo -e "\n$GREEN""$BOLD""  ==> Building Developent-Enviroment for EMBArk Done""$NC"
# else 
#  echo -e "\n$RED""$BOLD""  ==> Building Developent-Enviroment for EMBArk FAILED""$NC"
# fi
echo -e "\n$ORANGE""$BOLD""Done. To clean-up use the clean-setup script""$NC"
cd ..