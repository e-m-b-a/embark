#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2022 Siemens Energy AG
# Copyright 2020-2022 Siemens AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Starts the EMBArk on host

export GREEN='\033[0;32m'
export RED='\033[0;31m'
export ORANGE='\033[0;33m'
export BLUE='\033[0;34m'
export BOLD='\033[1m'
export NC='\033[0m'

export HELP_DIR='helper'

export DJANGO_SETTINGS_MODULE=embark.settings.deploy
export HTTP_PORT=80
export HTTPS_PORT=443
export BIND_IP='0.0.0.0'
export FILE_SIZE=2000000000
export SERVER_ALIAS=()
export WSGI_FLAGS=()

STRICT_MODE=0

import_helper()
{
  local HELPERS=()
  local HELPER_COUNT=0
  local HELPER_FILE=""
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
  # docker network rm embark_backend
  # docker container prune -f --filter "label=flag"

  systemctl stop embark.service
  exit 1
}


# main
echo -e "\\n$ORANGE""$BOLD""EMBArk Startup""$NC\\n""$BOLD=================================================================$NC"

while getopts "ha:" OPT ; do
  case $OPT in
    h)
      echo -e "\\n""$CYAN""USAGE""$NC"
      echo -e "$CYAN-h$NC           Print this help message"
      echo -e "$CYAN-a <IP/Name>$NC Add a server Domain-name alias"
      echo -e "---------------------------------------------------------------------------"
      if ip addr show eth0 &>/dev/null ; then
        IP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
        echo -e "$GREEN Suggestion:$NC  sudo ./run-server.sh -a $IP"
        echo -e "$GREEN nslookup helper:$NC"
        nslookup "$IP"
      fi
      exit 0
      ;;
    a)
      SERVER_ALIAS+=("$OPTARG")
      WSGI_FLAGS+=(--server-alias "${OPTARG}")
      ;;
    :)
      echo -e "$CYAN Usage: [-a <IP/HOSTNAME>] $NC"
      exit 1
      ;;
    *)
      echo -e "\\n$ORANGE""$BOLD""No Alias set""$NC\\n"
      ;;
  esac
done

# Alias
if [[ ${#SERVER_ALIAS[@]} -ne 0 ]]; then
  echo -e "$GREEN Server-alias:$NC"
  for VAR in "${SERVER_ALIAS[@]}"; do
    echo "[*] $VAR"
  done
fi

cd "$(dirname "$0")" || exit 1
import_helper
enable_strict_mode "$STRICT_MODE"
set -a
trap cleaner INT

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

# check venv 
if ! [[ -d /var/www/.venv ]]; then
  echo -e "$RED""$BOLD""Pip-enviroment not found!""$NC"
  exit 1
fi
if ! nc -zw1 google.com 443 &>/dev/null ; then
  (cd /var/www && pipenv check && pipenv verify)
fi

# copy emba
if [[ -d /var/www/emba ]]; then
  rm -Rf /var/www/emba
fi
cp -Ru ./emba/ /var/www/emba/

# Start container
echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
if docker-compose -f ./docker-compose.yml up -d ; then
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
if [[ -d /var/www/embark ]]; then
  rm -Rf /var/www/embark
fi
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
copy_file "$PWD"/cert/embark.local.crt /var/www/conf/cert
copy_file "$PWD"/cert/embark.local.key /var/www/conf/cert
copy_file "$PWD"/cert/embark-ws.local.key /var/www/conf/cert
copy_file "$PWD"/cert/embark-ws.local.crt /var/www/conf/cert

# cp .env
copy_file ./.env /var/www/embark/embark/settings/

# !DIRECTORY-CHANGE!
cd /var/www/embark/ || exit 1

# start venv (ignore source in script)
# shellcheck disable=SC1091
source /var/www/.venv/bin/activate || exit 1
export PIPENV_VERBOSITY=-1

# TODO move to parent
# logs
if ! [[ -d /var/www/logs ]]; then
  mkdir /var/www/logs
fi

# db_init
echo -e "\n[""$BLUE JOB""$NC""] Starting migrations - log to embark/logs/migration.log"
# pipenv run ./manage.py makemigrations | tee -a /var/www/logs/migration.log
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
--processes 4 --threads 4 \
--graceful-timeout 5 \
--server-name embark.local "${WSGI_FLAGS[@]}" &
# --ssl-certificate /var/www/conf/cert/embark.local --ssl-certificate-key-file /var/www/conf/cert/embark.local.key \
# --https-port "$HTTPS_PORT" &
#  --https-only --enable-debugger \
sleep 5

echo -e "\n[""$BLUE JOB""$NC""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
pipenv run daphne --access-log /var/www/logs/daphne.log -e ssl:8000:privateKey=/var/www/conf/cert/embark-ws.local.key:certKey=/var/www/conf/cert/embark-ws.local.crt -b "$BIND_IP" -p 8001 -s embark-ws.local --root-path=/var/www/embark embark.asgi:application &
sleep 5


echo -e "\n""$ORANGE$BOLD""=============================================================""$NC"
echo -e "\n""$ORANGE$BOLD""Server started on http://embark.local with alias:""${SERVER_ALIAS[*]}""$NC"
echo -e "\n""$ORANGE$BOLD""EMBA logs are under /var/www/emba_logs/<id> ""$NC"
# echo -e "\n""$ORANGE$BOLD""For SSL you may use https://embark.local (Not recommended for local use)""$NC"
# echo -e "\n\n""$GREEN$BOLD""the trusted rootCA.key for the ssl encryption is in ./cert""$NC"
wait