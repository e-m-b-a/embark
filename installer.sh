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
# Author(s): Michael Messner, Pascal Eckmann

# Description: Installer for EMBArk

export DEBIAN_FRONTEND=noninteractive

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

print_help() {
  echo -e "\\n""$CYAN""USAGE""$NC"
  echo -e "$CYAN-F$NC         Installation of EMBArk with all dependencies (typical initial installation)"
  echo -e "$CYAN-r$NC         Reinstallation of EMBArk with all dependencies (cleanup of docker environment first)"
  echo -e "$CYAN-e$NC         Install emba only"
  echo -e "$CYAN-h$NC         Print this help message"
  echo
}

install_emba() {
  echo -e "\n$GREEN""$BOLD""Installation of the firmware scanner emba""$NC"

  if [[ "$REFORCE" -eq 1 && -d ./emba ]]; then
    rm ./emba -r
  fi

  if ! [[ -d ./emba ]]; then
    git clone https://github.com/e-m-b-a/emba.git
  else
    cd emba || exit 1
    git pull
    cd .. || exit 1
  fi

  cd emba || exit 1
  ./installer.sh -F
  cd .. || exit 1
}

reset_docker() {
  echo -e "\n$GREEN""$BOLD""Reset EMBArk docker images""$NC"

  docker images
  docker container ls -a

  if docker images | grep -qE "^embark[[:space:]]*latest"; then
    echo -e "\n$GREEN""$BOLD""Found EMBArk docker environment - removing it""$NC"
    CONTAINER_ID=$(docker container ls -a | grep -E "embark_embark_1" | awk '{print $1}')
    echo -e "$GREEN""$BOLD""Stop EMBArk docker container""$NC"
    docker container stop "$CONTAINER_ID"
    echo -e "$GREEN""$BOLD""Remove EMBArk docker container""$NC"
    docker container rm "$CONTAINER_ID" -f
    echo -e "$GREEN""$BOLD""Remove EMBArk docker image""$NC"
    docker image rm embark:latest -f
  fi

  if docker images | grep -qE "^mysql[[:space:]]*latest"; then
    echo -e "\n$GREEN""$BOLD""Found mysql docker environment - removing it""$NC"
    CONTAINER_ID=$(docker container ls -a | grep -E "embark_auth-db_1" | awk '{print $1}')

    echo -e "$GREEN""$BOLD""Stop mysql docker container""$NC"
    docker container stop "$CONTAINER_ID"
    echo -e "$GREEN""$BOLD""Remove mysql docker container""$NC"
    docker container rm "$CONTAINER_ID" -f
    echo -e "$GREEN""$BOLD""Remove mysql docker image""$NC"
    docker image rm mysql:latest -f
  fi

  if docker images | grep -qE "^redis[[:space:]]*5"; then
    echo -e "\n$GREEN""$BOLD""Found redis docker environment - removing it""$NC"
    CONTAINER_ID=$(docker container ls -a | grep -E "embark_redis_1" | awk '{print $1}')
    echo -e "$GREEN""$BOLD""Stop redis docker container""$NC"
    docker container stop "$CONTAINER_ID"
    echo -e "$GREEN""$BOLD""Remove redis docker container""$NC"
    docker container rm "$CONTAINER_ID" -f
    echo -e "$GREEN""$BOLD""Remove redis docker image""$NC"
    docker image rm redis:5 -f
  fi
}

install_embark() {
  echo -e "\n$GREEN""$BOLD""Installation of the firmware scanning environment EMBArk""$NC"

  echo -e "\n$GREEN""$BOLD""Downloading of external files, e.g. jQuery, for the offline usability of EMBArk""$NC"
  mkdir -p ./embark/static/external/{scripts,css}
  wget -O ./embark/static/external/scripts/jquery.js https://code.jquery.com/jquery-3.6.0.min.js
  wget -O ./embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js
  wget -O ./embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js
  wget -O ./embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js
  wget -O ./embark/static/external/css/jquery.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css
  wget -O ./embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css
  wget -O ./embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css

  if ! [[ -f .env ]]; then
    DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    echo -e "$ORANGE""$BOLD""Creating a default EMBArk configuration file .env""$NC"
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
    } >> .env
    echo -e "$ORANGE""$BOLD""WARNING: The default EMBArk configuration includes a secret key generated via the shell script!""$NC"
    cat .env
  else
    echo -e "$GREEN""$BOLD""Using the provided EMBArk configuration file .env""$NC"
    cat .env
  fi

  echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
  docker-compose build
  DB_RETURN=$?
  if [[ $DB_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
  fi

  echo -e "\n$GREEN""$BOLD""Setup mysql and redis docker images""$NC"
  docker-compose up -d
  DU_RETURN=$?
  if [[ $DU_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
  fi

  echo -e "\n$GREEN""$BOLD""Restarting EMBArk docker images""$NC"
  docker-compose restart embark
  DS_RETURN=$?
  if [[ $DS_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished restarting EMBArk docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed restarting EMBArk docker images""$NC"
  fi

  echo -e "$GREEN""$BOLD""Testing EMBArk installation""$NC"
  # need to wait a few seconds until everyting is up and running
  sleep 5
  if curl -XGET 'http://0.0.0.0:80' | grep -q embark; then
    echo -e "$GREEN""$BOLD""Finished installing EMBArk""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed installing EMBArk - check the output from the installation process""$NC"
  fi

  echo -e "$GREEN""$BOLD""Setup your initial user with:""$NC"
  echo -e "curl -XPOST 'http://0.0.0.0:80/signup' -d '{\"email\": \"test@gmail.com\", \"password\": \"test\", \"confirm_password\": \"test\"}'"
}

install_debs() {
  echo -e "\n$GREEN""$BOLD""Install debian packages for EMBArk installation""$NC"
  apt-get update -y
  if ! command -v git > /dev/null ; then
    apt-get install -y -q git
  fi
  if ! command -v docker > /dev/null ; then
    apt-get install -y -q docker.io
  fi
  if ! command -v docker-compose > /dev/null ; then
    apt-get install -y -q docker-compose
  fi
  if ! command -v pycodestyle > /dev/null ; then
    apt-get install -y -q pycodestyle
  fi
  if ! command -v pylint > /dev/null ; then
    apt-get install -y -q pylint
    apt-get install -y -q python3-pylint-django
  fi
  # we need the django package on the host for generating the django SECRET_KEY
  apt-get install -y -q python3-django
}

echo -e "\\n$ORANGE""$BOLD""EMBArk Installer""$NC\\n""$BOLD=================================================================$NC"
echo -e "$ORANGE""$BOLD""WARNING: This script can harm your environment!""$NC"

if [ "$#" -ne 1 ]; then
  echo -e "$RED""$BOLD""Invalid number of arguments""$NC"
  print_help
  exit 1
fi

while getopts eFrh OPT ; do
  case $OPT in
    e)
      export EMBA_ONLY=1
      echo -e "$GREEN""$BOLD""Install only emba""$NC"
      ;;
    F)
      export FORCE=1
      echo -e "$GREEN""$BOLD""Install all dependecies""$NC"
      ;;
    r)
      export REFORCE=1
      echo -e "$GREEN""$BOLD""Install all dependecies including docker cleanup""$NC"
      ;;
    h)
      print_help
      exit 0
      ;;
    *)
      echo -e "$RED""$BOLD""Invalid option""$NC"
      print_help
      exit 1
      ;;
  esac
done

if ! [[ $EUID -eq 0 ]] && [[ $LIST_DEP -eq 0 ]] ; then
  echo -e "\\n$RED""Run EMBArk installation script with root permissions!""$NC\\n"
  print_help
  exit 1
fi

install_debs

install_emba

if [[ "$EMBA_ONLY" -ne 1 ]]; then

  if ! [[ -d embark/logs ]]; then
    mkdir embark/logs
  fi

  if [[ "$REFORCE" -eq 1 ]]; then
    reset_docker
  fi
  install_embark
fi

