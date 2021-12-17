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

# Description: Starts the Django-Server(s) on host

cleaner() {
  /app/mod_wsgi-express-80/apachectl stop
  fuser -k 80/tcp
  killall -9 -q "*daphne*"
  fuser -k 8001/tcp
  docker container stop embark_db_dev
  docker container stop embark_redis_dev
  docker network rm embark_dev
  docker container prune
  exit 1
}
set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1

if ! [[ $EUID -eq 0 ]] && [[ $LIST_DEP -eq 0 ]] ; then
  echo -e "\\n$RED""Run EMBArk installation script with root permissions!""$NC\\n"
  exit 1
fi

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color

export DJANGO_SETTINGS_MODULE=embark.settings

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f ./docker-compose-dev.yml up -d
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

# container-logs
echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
docker container logs embark_redis_dev -f &> ./embark/logs/redis_dev.log & 
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
docker container logs embark_db_dev -f &> ./embark/logs/mysql_dev.log &

# collect staticfiles
pipenv run ./embark/manage.py collectstatic --noinput

#echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
#pipenv run ./manage.py runapscheduler | tee -a ./logs/scheduler.log &

echo -e "\n[""$BLUE JOB""$NC""] Starting wsgi - log to /embark/logs/wsgi.log"
pipenv run ./embark/manage.py runmodwsgi --working-directory . #--port=80 --user www-data --group www-data --server-root=/app/mod_wsgi-express-80 --document-root ./www/static --allow-localhost
#--setup-only 
#/app/mod_wsgi-express-80/apachectl start

#echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
#pipenv run daphne -v 3 --access-log ./embark/logs/daphne.log -p 8001 -b '0.0.0.0' --root-path="./embark" embark.embark.asgi:application

wait %1
wait %2
