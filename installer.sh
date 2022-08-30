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
# Author(s): Michael Messner, Pascal Eckmann
# Contributor(s): Benedikt Kuehne

# Description: Installer for EMBArk

# it the installer fails you can try to change it to 0
STRICT_MODE=1

export DEBIAN_FRONTEND=noninteractive

export HELP_DIR='helper'

export REFORCE=0
export UNINSTALL=0
export DEFAULT=0
export DEV=0
export EMBA_ONLY=0
export DOCKER=0

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export ORANGE='\033[0;33m'
export CYAN='\033[0;36m'
export BOLD='\033[1m'
export NC='\033[0m' # no 

print_help() {
  echo -e "\\n""$CYAN""USAGE""$NC"
  echo -e "$CYAN-h$NC         Print this help message"
  echo -e "$CYAN-d$NC         EMBArk default installation"
  echo -e "$CYAN-F$NC         Installation of EMBArk for developers"
  echo -e "$CYAN-e$NC         Install EMBA only"
  echo -e "$CYAN-D$NC         Install for Docker deployment"
  echo -e "---------------------------------------------------------------------------"
  echo -e "$CYAN-U$NC         Uninstall EMBArk"
  echo -e "$CYAN-rd$NC        Reinstallation of EMBArk with all dependencies"
  echo -e "$CYAN-rF$NC        Reinstallation of EMBArk with all dependencies in Developer-mode"
  echo -e "$RED               ! Both options delete all Database-files as well !""$NC"
}

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

# Source: https://stackoverflow.com/questions/4023830/how-to-compare-two-strings-in-dot-separated-version-format-in-bash
version() { echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'; }

write_env() {
  local SUPER_PW="embark"
  local SUPER_EMAIL="idk@lol.com"
  local SUPER_USER="superuser"

  local RANDOM_PW=""
  local DJANGO_SECRET_KEY=""
  
  DJANGO_SECRET_KEY=$(python3.10 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
  RANDOM_PW=$(openssl rand -base64 12)
  
  echo -e "$ORANGE""$BOLD""Creating a EMBArk configuration file .env""$NC"
  {
    echo "DATABASE_NAME=embark"
    echo "DATABASE_USER=embark" 
    echo "DATABASE_PASSWORD=$RANDOM_PW"
    echo "DATABASE_HOST=172.22.0.5"
    echo "DATABASE_PORT=3306"
    echo "MYSQL_PASSWORD=$RANDOM_PW"
    echo "MYSQL_USER=embark"
    echo "MYSQL_DATABASE=embark"
    echo "REDIS_HOST=172.22.0.8"
    echo "REDIS_PORT=7777"
    echo "SECRET_KEY=$DJANGO_SECRET_KEY"
    echo "DJANGO_SUPERUSER_USERNAME=$SUPER_USER"
    echo "DJANGO_SUPERUSER_EMAIL=$SUPER_EMAIL"
    echo "DJANGO_SUPERUSER_PASSWORD=$SUPER_PW"
    echo "PYTHONPATH=${PWD}:/var/www/:/var/www/embark"
  } > .env
  chmod 600 .env
}

install_emba() {
  echo -e "\n$GREEN""$BOLD""Installation of the firmware scanner EMBA on host""$NC"
  sudo -u "${SUDO_USER:-${USER}}" 'git submodule init'
  sudo -u "${SUDO_USER:-${USER}}" 'git submodule update --remote --merge'
  sudo -u "${SUDO_USER:-${USER}}" "git config --global --add safe.directory ""$PWD""/emba"
  cd emba || ( echo "Could not install EMBA" && exit 1 )
  ./installer.sh -d || ( echo "Could not install EMBA" && exit 1 )
  if ! [[ -f /etc/cron.daily/emba_updater ]]; then
    cp ./config/emba_updater /etc/cron.daily/
  fi
  cd .. || ( echo "Could not install EMBA" && exit 1 )
  chown -R "${SUDO_USER:-${USER}}" emba
  echo -e "\n""--------------------------------------------------------------------""$NC"
}

create_ca (){
  # TODO could use some work 
  echo -e "\n$GREEN""$BOLD""Creating SSL Cert""$NC"
  cd cert || exit 1
  if [[ -f embark.local.csr ]] || [[ -f embark-ws.local.csr ]] || [[ -f embark.local.crt ]] || [[ -f embark-ws.local.crt ]]; then 
    echo -e "\n$GREEN""$BOLD""Certs already generated, skipping""$NC"
  else
    # create CA
    openssl genrsa -out rootCA.key 4096
    openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out rootCA.crt -subj '/CN=embark.local/O=EMBA/C=US'
    # create server sign requests (csr)
    openssl genrsa -out embark.local.key 2048
    openssl req -new -sha256 -key embark.local.key -out embark.local.csr  -subj '/CN=embark.local/O=EMBA/C=US'
    openssl genrsa -out embark-ws.local.key 2048
    openssl req -new -sha256 -key embark-ws.local.key -out embark-ws.local.csr  -subj '/CN=embark-ws.local/O=EMBA/C=US'
    # signe csr with ca
    openssl x509 -req -in embark.local.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out embark.local.crt -days 10000 -sha256
    openssl x509 -req -in embark-ws.local.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out embark-ws.local.crt -days 10000 -sha256
  fi
  cd .. || exit 1
}

dns_resolve(){
  echo -e "\n$GREEN""$BOLD""Install hostnames for local dns-resolve""$NC"
  if ! grep -q "embark.local" /etc/hosts ; then
    printf "0.0.0.0     embark.local\n" >>/etc/hosts
  else
    echo -e "\n$ORANGE""$BOLD""hostname already in use!""$NC"
  fi
}

reset_docker() {
  echo -e "\\n$GREEN""$BOLD""Reset EMBArk docker images""$NC\\n"

  # images
  docker_image_rm "mysql" "latest"
  docker_image_rm "redis" "5"
  docker_image_rm "embeddedanalyzer/emba" "latest"
  
  #networks
  docker_network_rm "embark_dev"
  # docker_network_rm "embark_frontend"
  docker_network_rm "embark_backend"
  docker_network_rm "emba_runs"

  docker container prune -f --filter "label=flag" || true

}

install_debs() {
  local DOCKER_COMP_VER=""
  echo -e "\n$GREEN""$BOLD""Install debian packages for EMBArk installation""$NC"
  apt-get update -y
  # Git
  if ! command -v git > /dev/null ; then
    apt-get install -y git
  fi
  # Python3
  if ! command -v python3.10 > /dev/null ; then
    apt-get install -y python3.10
  fi
  # Pip
  if ! command -v pip3.10 > /dev/null ; then
    apt-get install -y python3-pip
  fi
  # Gcc
  if ! command -v gcc > /dev/null ; then
    apt-get install build-essential
  fi
  # Docker
  if ! command -v docker > /dev/null ; then
    apt-get install -y docker.io
  fi
  # docker-compose
  if ! command -v docker-compose > /dev/null ; then
    pip3 install docker-compose --upgrade
    if ! [[ -d /usr/bin/docker-compose ]]; then
      ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    fi
  else
    DOCKER_COMP_VER=$(docker-compose -v | grep version | awk '{print $3}' | tr -d ',')
    if [[ $(version "$DOCKER_COMP_VER") -lt $(version "1.28.5") ]]; then
      echo -e "\n${ORANGE}WARNING: compatibility of the used docker-compose version is unknown!$NC"
      echo -e "\n${ORANGE}Please consider updating your docker-compose installation to version 1.28.5 or later.$NC"
      read -p "If you know what you are doing you can press any key to continue ..." -n1 -s -r
    fi
  fi
  # python3-dev
  if ! dpkg -l python3.10-dev &>/dev/null; then
      apt-get install -y python3.10-dev || apt-get install -y -q python3-dev
  fi
  #  python3-django
  if ! dpkg -l python3-django &>/dev/null; then
    apt-get install -y python3-django
  fi
}

install_daemon() {
  echo -e "\n$GREEN""$BOLD""Install embark daemon""$NC"
  sed -i "s|{\$EMBARK_ROOT_DIR}|$PWD|g" embark.service
  # FIXME test this
  ln -s "$PWD"/embark.service /etc/systemd/system/embark.service
}

install_embark_default() {
  echo -e "\n$GREEN""$BOLD""Installation of the firmware scanning environment EMBArk""$NC"
  
  #debs
  apt-get install -y -q default-libmysqlclient-dev build-essential
  
  # install pipenv
  pip3.10 install pipenv

  #Add user for server
  if ! cut -d: -f1 /etc/passwd | grep -E www-embark ; then
    useradd www-embark -G sudo -c "embark-server-user" -M -r --shell=/usr/sbin/nologin -d /var/www/embark
    echo 'www-embark ALL=(ALL) NOPASSWD: /var/www/emba/emba.sh' | EDITOR='tee -a' visudo
    echo 'www-embark ALL=(ALL) NOPASSWD: /bin/pkill' | EDITOR='tee -a' visudo
  fi

  #Server-Dir
  if ! [[ -d /var/www ]]; then
    mkdir /var/www/
  fi
  if ! [[ -d /var/www/media ]]; then
    mkdir /var/www/media
  fi
  if ! [[ -d /var/www/active ]]; then
    mkdir /var/www/active
  fi
  if ! [[ -d /var/www/emba_logs ]]; then
    mkdir /var/www/emba_logs
  fi
  if ! [[ -d /var/www/static ]]; then
    mkdir /var/www/static
  fi
  if ! [[ -d /var/www/conf ]]; then
    mkdir /var/www/conf
  fi

  # daemon
  install_daemon
  
  #add ssl cert
  create_ca

  #add dns name
  dns_resolve

  #install packages
  cp ./Pipfile* /var/www/
  (cd /var/www && PIPENV_VENV_IN_PROJECT=1 pipenv install)
  

  # download externals
  if ! [[ -d ./embark/static/external ]]; then
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

  # write env-vars into ./.env
  write_env

  # download images for container
  docker-compose -f ./docker-compose.yml up --no-start
  docker-compose -f ./docker-compose.yml up &>/dev/null &
  sleep 30
  kill %1

  # activate daemon
  systemctl start embark.service

  echo -e "$GREEN""$BOLD""Ready to use \$sudo ./run-server.sh ""$NC"
  echo -e "$GREEN""$BOLD""Which starts the server on (0.0.0.0) port 80 ""$NC"
}

install_embark_dev(){
  echo -e "\n$GREEN""$BOLD""Building Developent-Enviroment for EMBArk""$NC"
  # apt packages
  apt-get install -y npm pycodestyle python3-pylint-django default-libmysqlclient-dev build-essential pipenv bandit
  # npm packages
  npm install -g jshint dockerlinter
  
  # install pipenv
  pip3.10 install pipenv

  #Add user nosudo
  echo "${SUDO_USER:-${USER}}"" ALL=(ALL) NOPASSWD: ""$PWD""/emba/emba.sh" | EDITOR='tee -a' visudo
  echo "${SUDO_USER:-${USER}}"" ALL=(ALL) NOPASSWD: /bin/pkill" | EDITOR='tee -a' visudo
  

  #pipenv
  PIPENV_VENV_IN_PROJECT=1 pipenv install --dev

  # download externals
  if ! [[ -d ./embark/static/external ]]; then
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

  # write env-vars into ./.env
  write_env

  # daemon
  # install_daemon

  echo -e "$GREEN""$BOLD""Ready to use \$sudo ./dev-tools/debug-server-start.sh""$NC"
  echo -e "$GREEN""$BOLD""Or use otherwise""$NC"
}

#install as docker-service # TODO
install_embark_docker(){
  echo -e "\n$GREEN""$BOLD""Installing EMBArk as docker-container""$NC"

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
  echo -e "$ORANGE""$BOLD""Creating a container EMBArk configuration file .env""$NC"
  export DATABASE_NAME="embark"
  export DATABASE_USER="embark"
  export DATABASE_PASSWORD="$RANDOM_PW"
  export DATABASE_HOST="172.23.0.5"
  export DATABASE_PORT="3306"
  export MYSQL_PASSWORD="$RANDOM_PW"
  export MYSQL_USER="embark"
  export MYSQL_DATABASE="embark"
  export REDIS_HOST="172.23.0.8"
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

  # setup dbs-container and detach build could be skipt
  echo -e "\n$GREEN""$BOLD""Building EMBArk docker images""$NC"
  docker-compose -f ./docker-compose-docker.yml build
  DB_RETURN=$?
  if [[ $DB_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished building EMBArk docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed building EMBArk docker images""$NC"
  fi

  echo -e "\n$GREEN""$BOLD""Starting EMBArk docker images""$NC"
  docker-compose -f ./docker-compose-docker.yml up -d
  DS_RETURN=$?
  if [[ $DS_RETURN -eq 0 ]] ; then
    echo -e "$GREEN""$BOLD""Finished starting EMBArk""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed starting EMBArk""$NC"
  fi

  echo -e "$GREEN""$BOLD""Testing EMBArk installation""$NC"
  # need to wait a few seconds until everyting is up and running
  sleep 5
  if ! curl -XGET 'http://0.0.0.0:80' | grep -q embark; then
    echo -e "$ORANGE""$BOLD""Failed installing EMBArk - check the output from the installation process""$NC"
  fi

  echo -e "$GREEN""$BOLD""Server ready to use""$NC"
  echo -e "$GREEN""EMBArk is on (0.0.0.0) port 80 ""$NC"
}

uninstall (){
  echo -e "[+]$CYAN""$BOLD""Uninstalling EMBArk""$NC"

  # delete symlink (legacy)
  echo -e "$ORANGE""$BOLD""Delete Symlink?""$NC"
  if ! [[ -f /app ]]; then
    if [[ $( readlink /app ) == "$PWD" ]]; then
      rm /app
    fi
  fi

  # delete directories
  echo -e "$ORANGE""$BOLD""Delete Directories""$NC"
  if [[ -d /var/www ]]; then
    rm -Rv /var/www
  fi
  if [[ -d ./media ]]; then
    rm -Rv ./media
  fi
  if [[ -d ./active ]]; then
    rm -Rv ./active
  fi
  if [[ -d ./static ]]; then
    rm -Rv ./static
  fi
  if [[ -d ./cert ]]; then
    rm -Rv ./cert
  fi
  if [[ -d ./.venv ]]; then
    rm -Rvf ./.venv
  fi
  if [[ "$REFORCE" -eq 0 ]]; then
    # user-files
    if [[ -d ./emba_logs ]]; then
      echo -e "$RED""$BOLD""Do you wish to remove the EMBA-Logs (and backups)""$NC"
      rm -Riv ./emba_logs
    fi
    if [[ -d ./embark_db ]]; then
      echo -e "$RED""$BOLD""Do you wish to remove the database(and backups)""$NC"
      rm -RIv ./embark_db
    fi
  fi


  # delete user www-embark and reset visudo
  echo -e "$ORANGE""$BOLD""Delete user""$NC"
  # sed -i 's/www\-embark\ ALL\=\(ALL\)\ NOPASSWD\:\ \/app\/emba\/emba.sh//g' /etc/sudoers #TODO doesnt work yet
  if id -u www-embark &>/dev/null ; then
    userdel www-embark
  fi

  # delete .env
  echo -e "$ORANGE""$BOLD""Delete env""$NC"
  if [[ -f ./.env ]]; then
    rm ./.env
  fi

  # delete shared volumes and migrations
  echo -e "$ORANGE""$BOLD""Delete migration-files""$NC"
  find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
  find . -path "*/migrations/*.pyc"  -delete

  # delete all docker interfaces and containers + images
  reset_docker
  echo -e "$ORANGE""$BOLD""Consider running " "$CYAN""\$docker system prune""$NC"

  # delete/uninstall EMBA
  sudo -u "${SUDO_USER:-${USER}}" git submodule foreach git reset --hard
  sudo -u "${SUDO_USER:-${USER}}" git submodule deinit --all -f

  # stop&reset daemon
  if [[ -e /etc/systemd/system/embark.service ]] ; then
    systemctl stop embark.service
    systemctl disable embark.service
  fi
  sudo -u "${SUDO_USER:-${USER}}" git checkout HEAD -- embark.service
  systemctl daemon-reload

  # reset ownership etc
  # TODO delete the dns resolve

  # reset server-certs
  sudo -u "${SUDO_USER:-${USER}}" git checkout HEAD -- cert

  # final
  if [[ "$REFORCE" -eq 0 ]]; then
    sudo -u "${SUDO_USER:-${USER}}" git reset
  fi
  echo -e "$ORANGE""$BOLD""Consider""$CYAN""\$git pull""$NC"
}

echo -e "\\n$ORANGE""$BOLD""EMBArk Installer""$NC\\n""$BOLD=================================================================$NC"
echo -e "$ORANGE""$BOLD""WARNING: This script can harm your environment!""$NC\n"

import_helper

if [[ "$STRICT_MODE" -eq 1 ]]; then
  # http://redsymbol.net/articles/unofficial-bash-strict-mode/
  # https://github.com/tests-always-included/wick/blob/master/doc/bash-strict-mode.md
  set -e                # Exit immediately if a command exits with a non-zero status
  set -u                # Exit and trigger the ERR trap when accessing an unset variable
  set -o pipefail       # The return value of a pipeline is the value of the last (rightmost) command to exit with a non-zero status
  set -E                # The ERR trap is inherited by shell functions, command substitutions and commands in subshells
  shopt -s extdebug     # Enable extended debugging
  IFS=$'\n\t'           # Set the "internal field separator"
  trap 'wickStrictModeFail $? | tee -a /tmp/embark_installer.log' ERR  # The ERR trap is triggered when a script catches an error
fi

if [ "$#" -ne 1 ]; then
  echo -e "$RED""$BOLD""Invalid number of arguments""$NC"
  print_help
  exit 1
fi

while getopts eFUrdDh OPT ; do
  case $OPT in
    e)
      export EMBA_ONLY=1
      echo -e "$GREEN""$BOLD""Install only emba""$NC"
      ;;
    F)
      export DEV=1
      echo -e "$GREEN""$BOLD""Building Development-Enviroment""$NC"
      ;;
    U)
      export UNINSTALL=1
      echo -e "$GREEN""$BOLD""Uninstall EMBArk""$NC"
      ;;
    r)
      export UNINSTALL=1
      export REFORCE=1
      echo -e "$GREEN""$BOLD""Re-Install all dependecies while keeping user-files""$NC"
      ;;
    d)
      export DEFAULT=1
      echo -e "$GREEN""$BOLD""Default installation of EMBArk""$NC"
      ;;
    D)
      export DOCKER=1
      echo -e "$GREEN""$BOLD""Install all dependecies for EMBArk-docker-container""$NC"
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

if [[ $REFORCE -eq 1 ]] && [[ $UNINSTALL -eq 1 ]]; then
  uninstall
elif [[ $UNINSTALL -eq 1 ]]; then
  uninstall
  exit 0
fi

install_debs

# mark dir as safe for git
sudo -u "${SUDO_USER:-${USER}}" git config --global --add safe.directory "$PWD"

install_emba

if [[ $DEFAULT -eq 1 ]]; then
  install_embark_default
elif [[ $DEV -eq 1 ]]; then
  install_embark_dev
elif [[ $DOCKER -eq 1 ]]; then
  install_embark_docker
fi

exit 0
