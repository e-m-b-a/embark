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

# http-server options
PORT="8000"
IP="127.0.0.1"

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export ORANGE='\033[0;33m'
export BLUE='\033[0;34m'
export BOLD='\033[1m'
export NC='\033[0m' # no color

export DJANGO_SETTINGS_MODULE=embark.settings.dev

export WSL=0

cleaner() {
  pkill -u root daphne
  pkill -u root "$PWD"/emba/emba
  pkill -u root runapscheduler

  docker container stop embark_db
  docker container stop embark_redis

  # docker container prune -f --filter "label=flag"
  # rm embark_db/* -rf

  fuser -k "$PORT"/tcp
  chown "${SUDO_USER:-${USER}}" "$PWD" -R
  exit 1
}

import_helper()
{
  local HELPERS=()
  local HELPER_COUNT=0
  local HELPER_FILE=""
  local HELP_DIR='helper'
  mapfile -d '' HELPERS < <(find "$HELP_DIR" -iname "helper_embark_*.sh" -print0 2> /dev/null)
  for HELPER_FILE in "${HELPERS[@]}" ; do
    if ( file "$HELPER_FILE" | grep -q "shell script" ) && ! [[ "$HELPER_FILE" =~ \ |\' ]] ; then
      # https://github.com/koalaman/shellcheck/wiki/SC1090
      # shellcheck source=/dev/null
      source "$HELPER_FILE"
      (( HELPER_COUNT+=1 ))
    fi
  done
  echo -e "\\n""==> ""$GREEN""Imported ""$HELPER_COUNT"" necessary files""$NC\\n"
}

set -a
trap cleaner INT

cd "$(dirname "$0")" || exit 1

if ! [[ $EUID -eq 0 ]] ; then
  echo -e "\\n$RED""Run script with root permissions!""$NC\\n"
  exit 1
fi

cd .. || exit 1

echo "USER is ${SUDO_USER:-${USER}}"

import_helper

# WSL/OS version check
# WSL support - currently experimental!
if grep -q -i wsl /proc/version; then
  echo -e "\n${ORANGE}INFO: System running in WSL environment!$NC"
  echo -e "\n${ORANGE}INFO: WSL is currently experimental!$NC"
  WSL=1
fi

if [[ "$WSL" -eq 1 ]]; then
  check_docker_wsl
fi

# check emba
echo -e "$BLUE""$BOLD""checking EMBA""$NC"
if ! ./emba/emba -d 1>/dev/null ; then
  echo -e "$RED""EMBA is not configured correctly""$NC"
  exit 1
fi

echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
if docker-compose -f ./docker-compose.yml up -d ; then
  echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
else
  echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
  exit 1
fi

if ! [[ -d "$PWD"/logs ]]; then
  mkdir logs
fi

echo -e "\n[""$BLUE JOB""$NC""] Redis logs are copied to ./logs/redis_dev.log""$NC" 
docker container logs embark_redis -f > ./logs/redis_dev.log &
echo -e "\n[""$BLUE JOB""$NC""] DB logs are copied to ./logs/mysql_dev.log""$NC"
docker container logs embark_db -f > ./logs/mysql_dev.log & 

# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

# db_init
echo -e "[*] Starting migrations - log to embark/logs/migration.log"
python3 ./embark/manage.py makemigrations users uploader reporter dashboard | tee -a ./logs/migration.log
python3 ./embark/manage.py migrate | tee -a ./logs/migration.log

# superuser
python3 ./embark/manage.py createsuperuser --noinput

##
echo -e "\n[""$BLUE JOB""$NC""] Starting runapscheduler"
python3 ./embark/manage.py runapscheduler | tee -a ./logs/scheduler.log &

echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
echo "START DAPHNE" >./logs/daphne.log
cd ./embark || exit 1
pipenv run daphne -v 3 -p 8001 -b "$IP" --root-path="$PWD"/embark embark.asgi:application &>../logs/daphne.log &
cd .. || exit 1

# start embark
# systemctl start embark.service

echo -e "$ORANGE""$BOLD""start EMBArk server (WS/WSS not enabled -a also asgi)""$NC"
python3 ./embark/manage.py runserver "$IP":"$PORT" |& tee -a ./logs/debug-server.log

wait


echo -e "\n$ORANGE""$BOLD""Done. To clean-up use the clean-setup script""$NC"