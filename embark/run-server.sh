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
  echo -e "\\n$RED""Run EMBArk run-server script with root permissions! (Docker)""$NC\\n"
  exit 1
fi

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # no color

export DJANGO_SETTINGS_MODULE=embark.settings

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
docker-compose -f ../docker-compose-dev.yml up -d
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
pipenv run ./manage.py makemigrations users uploader | tee -a ./logs/migration.log
pipenv run ./manage.py migrate | tee -a ./logs/migration.log

# container-logs
echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./embark/logs/redis_dev.log""$NC" 
docker container logs embark_redis_dev -f &> ./logs/redis_dev.log & 
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./embark/logs/mysql_dev.log""$NC"
docker container logs embark_db_dev -f &> ./logs/mysql_dev.log & 

# run middlewears
# echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
# pipenv run ./manage.py runapscheduler --test | tee -a ./logs/scheduler.log &
echo -e "\n[""$BLUE JOB""$NC""] Starting uwsgi - log to /embark/logs/uwsgi.log"
pipenv run uwsgi --wsgi-file ./embark/wsgi.py --http :80 --threads 8 --logto ./logs/uwsgi.log &
echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
pipenv run daphne -v 3 --access-log ./logs/daphne.log -p 8001 -b '0.0.0.0' --root-path="$PWD" embark.asgi:application 1>/dev/null

wait %1
wait %2
wait %3