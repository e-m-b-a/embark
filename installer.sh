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
# Contributor(s): Benedikt Kuehne

# Description: Installer for EMBArk

export DEBIAN_FRONTEND=noninteractive

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

print_help() {
  echo -e "\\n""$CYAN""USAGE""$NC"
  # echo -e "$CYAN-F$NC         Installation of EMBArk with all dependencies (typical initial installation)"
  # echo -e "$CYAN-r$NC         Reinstallation of EMBArk with all dependencies (cleanup of docker environment first)"
  # echo -e "$RED               ! This deletes all Docker-Images as well !""$NC"
  echo -e "$CYAN-e$NC         Install EMBA only"
  echo -e "$CYAN-h$NC         Print this help message"
  echo -e "$CYAN-d$NC         Build EMBArk"  # Webserver on host
  echo
}

install_emba() {
  echo -e "\n$GREEN""$BOLD""Installation of the firmware scanner EMBA on host""$NC"

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

  
  # while docker images | grep -qE "^\<none\>"; do
  #   IMAGE_ID=$(docker container| grep -E "^\<none\>" | awk '{print $3}')
  #   echo -e "$GREEN""$BOLD""Remove failed docker image""$NC"
  #   docker image rm "$IMAGE_ID"
  # done

  if docker images | grep -qE "^embeddedanalyzer/emba"; then
    echo -e "\n$GREEN""$BOLD""Found EMBA docker environment - removing it""$NC"
    CONTAINER_ID=$(docker image ls | grep -E "embeddedanalyzer/emba" | awk '{print $3}')
    echo -e "$GREEN""$BOLD""Remove EMBA docker image""$NC"
    docker image rm "$IMAGE_ID"
  fi

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
  wget -O ./embark/static/external/scripts/confirm.js https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js
  wget -O ./embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js
  wget -O ./embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js
  wget -O ./embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js
  wget -O ./embark/static/external/css/confirm.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css
  wget -O ./embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css
  wget -O ./embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css
  find ./embark/static/external/ -type f -exec sed -i '/sourceMappingURL/d' {} \;

  # generating dynamic authentication for backend
  # for MYSQL root pwd check the logs of the container
  if ! [[ -f .env ]]; then
    DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    PASSWORD=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 13 )
    echo -e "$ORANGE""$BOLD""Creating a default EMBArk configuration file .env""$NC"
    export DATABASE_NAME="embark"
    export DATABASE_USER="embark"
    export DATABASE_PASSWORD="$PASSWORD"
    export DATABASE_HOST="127.0.0.1"
    export DATABASE_PORT="3306"
    export MYSQL_PASSWORD="$PASSWORD"
    export MYSQL_USER="embark"
    export MYSQL_DATABASE="embark"
    export REDIS_HOST="127.0.0.1"
    export REDIS_PORT="7777"
    export SECRET_KEY="$DJANGO_SECRET_KEY"
    # this is for pipenv/django # TODO change/lock after deploy
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
      echo "PYTHONPATH=${PYTHONPATH}:${PWD}:${PWD}/embark/"
    } > .env
    echo -e "$RED""$BOLD""WARNING: The default EMBArk configuration includes a key & password generation via the shell script!""$NC"
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
  
  # TODO compose work without restart
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

  echo -e "$GREEN""$BOLD""Ready to use @ localhost:80""$NC"
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
  # we need the django package on the host for generating the django SECRET_KEY and pip
  apt-get install -y -q python3-django python3-pip
}

# TODO this or install_embark NOT both in the same directory
make_dev_env(){
  echo -e "\n$GREEN""$BOLD""Building Developent-Enviroment for EMBArk""$NC"
  install_debs
  apt-get install -y -q python3-dev default-libmysqlclient-dev build-essential sqlite3 pipenv npm pycodestyle python3-pylint-django
  npm install -g jshint # global install
  pipenv install --dev
  # download externals
  if ! [[ -d embark/static/external ]]; then
    echo -e "\n$GREEN""$BOLD""Downloading of external files, e.g. jQuery, for the offline usability of EMBArk""$NC"
    mkdir -p ./embark/static/external/{scripts,css}
    wget -O ./embark/static/external/scripts/jquery.js https://code.jquery.com/jquery-3.6.0.min.js
    wget -O ./embark/static/external/scripts/confirm.js https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js
    wget -O ./embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/js/bootstrap.bundle.min.js
    wget -O ./embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js
    wget -O ./embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js
    wget -O ./embark/static/external/css/confirm.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css
    wget -O ./embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.1.1/dist/css/bootstrap.min.css
    wget -O ./embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css
    find ./embark/static/external/ -type f -exec sed -i '/sourceMappingURL/d' {} \;
  fi
  # get emba
  if ! [[ -d ./emba ]]; then
    git clone https://github.com/e-m-b-a/emba.git
  else
    cd emba || exit 1
    RES=$(git pull;)
    cd .. || exit 1
  fi

  # install on host 
  if ! [[ "$RES" == "Already up to date." ]]; then
    cd emba || exit 1
    ./installer.sh -d
    cd .. || exit 1
  fi

  #Add Symlink
  if ! [[ -d /app ]]; then
    ln -s "$PWD" /app || exit 1
  fi
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
    echo "PYTHONPATH=${PYTHONPATH}:${PWD}"  #TODO
  } > ./.env
  # setup dbs-container and detach build could be skipt
    echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
  docker-compose -f ./docker-compose-dev.yml build
  DB_RETURN=$?
  if [[ $DB_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
  fi
  # download images for container
  docker-compose -f ./docker-compose-dev.yml up --no-start
  docker-compose -f ./docker-compose-dev.yml up &>/dev/null &
  sleep 30
  kill %1

  echo -e "$GREEN""$BOLD""Ready to use \$sudo ./embark/run-server.sh ""$NC"
  echo -e "$GREEN""$BOLD""Which starts the server on (0.0.0.0) port 80 ""$NC"
}

echo -e "\\n$ORANGE""$BOLD""EMBArk Installer""$NC\\n""$BOLD=================================================================$NC"
echo -e "$ORANGE""$BOLD""WARNING: This script can harm your environment!""$NC"

if [ "$#" -ne 1 ]; then
  echo -e "$RED""$BOLD""Invalid number of arguments""$NC"
  print_help
  exit 1
fi

while getopts eFrdh OPT ; do
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
    d)
      export DEV=1
      echo -e "$GREEN""$BOLD""Building Development-Enviroment""$NC"
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

if [[ "$DEV" -eq 1 ]]; then
    make_dev_env
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

