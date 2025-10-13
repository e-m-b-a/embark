#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2025 Siemens Energy AG
# Copyright 2020-2022 Siemens AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Michael Messner, Pascal Eckmann, Benedikt Kuehne
# Contributor(s): ClProsser

# Description: Installer for EMBArk

# it the installer fails you can try to change it to 0
STRICT_MODE=0

export DEBIAN_FRONTEND=noninteractive

export HELP_DIR='helper'

export REFORCE=0
export UNINSTALL=0
export DEFAULT=0
export DEV=0
export EMBA_ONLY=0
export NO_EMBA=0
export NO_GIT=0

export WSL=0
export OS_TYPE="debian"

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export ORANGE='\033[0;33m'
export CYAN='\033[0;36m'
export BOLD='\033[1m'
export NC='\033[0m' # no

print_help(){
  echo -e "\\n""${CYAN}""USAGE""${NC}"
  echo -e "${CYAN}-h${NC}         Print this help message"
  echo -e "${CYAN}-d${NC}         EMBArk default installation"
  echo -e "${CYAN}-F${NC}         Installation of EMBArk for developers"
  echo -e "${CYAN}-e${NC}         Install EMBA only"
  echo -e "${CYAN}-s${NC}         Installation without EMBA (use in combination with d/F)"
  echo -e "---------------------------------------------------------------------------"
  echo -e "${CYAN}-U${NC}         Uninstall EMBArk"
  echo -e "${CYAN}-rd${NC}        Reinstallation of EMBArk with all dependencies"
  echo -e "${CYAN}-rF${NC}        Reinstallation of EMBArk with all dependencies in Developer-mode"
  echo -e "${RED}               ! Both options delete all Database-files as well !""${NC}"
}

import_helper(){
  local HELPERS=()
  local HELPER_COUNT=0
  local HELPER_FILE=""
  mapfile -d '' HELPERS < <(find "${HELP_DIR}" -iname "helper_embark_*.sh" -print0 2> /dev/null)
  for HELPER_FILE in "${HELPERS[@]}" ; do
    if ( file "${HELPER_FILE}" | grep -q "shell script" ) && ! [[ "${HELPER_FILE}" =~ \ |\' ]] ; then
      # https://github.com/koalaman/shellcheck/wiki/SC1090
      # shellcheck source=/dev/null
      source "${HELPER_FILE}"
      (( HELPER_COUNT+=1 ))
    fi
  done
  echo -e "\\n""==> ""${GREEN}""Imported ""${HELPER_COUNT}"" necessary files""${NC}\\n"
}

# Source: https://stackoverflow.com/questions/4023830/how-to-compare-two-strings-in-dot-separated-version-format-in-bash
# version(){ echo "$@" | awk -F. '{ printf("%d%03d%03d%03d\n", $1,$2,$3,$4); }'; }

save_old_env(){
  if ! [[ -d ./safe ]]; then
    mkdir safe
  fi
  if [[ -f ./.env ]]; then
    cp ./.env ./safe/"$(date +'%m-%d-%Y').env"
  fi
}

write_env(){
  local SUPER_PW=""
  SUPER_PW="$(openssl rand -base64 8)"
  local SUPER_EMAIL="admin@embark.local"
  local SUPER_USER="admin"
  local RANDOM_PW=""
  local DJANGO_SECRET_KEY=""
  local ENV_FILES=()
  local LAST_PW_HASH=""
  local CHECK_PW=""

  if [[ -d safe ]]; then
    mapfile -d '' ENV_FILES < <(find ./safe -iname "*.env" -print0 2> /dev/null)
    if [[ ${#ENV_FILES[@]} -gt 0 ]] && [[ -f safe/history.env ]]; then
      echo -e "${ORANGE}""${BOLD}""Using old env file""${NC}"
      # check which env file was the last one where $(echo "${PASSWORD_}" | sha256sum) matches the first line and entry
      LAST_PW_HASH="$(grep -v "$(echo "" | sha256sum)" safe/history.env | tail -n 1 | cut -d";" -f1)"
      for FILE_ in "${ENV_FILES[@]}"; do
        CHECK_PW="$(grep "DATABASE_PASSWORD=" "${FILE_}" | sed -e "s/^DATABASE_PASSWORD=//" )"
        if [[ "${LAST_PW_HASH}" == "$(echo "${CHECK_PW}" | sha256sum)" ]]; then
          RANDOM_PW="${CHECK_PW}"
          DJANGO_SECRET_KEY="$(grep "SECRET_KEY=" "${FILE_}" | sed -e "s/^SECRET_KEY=//" )"
          SUPER_PW="$(grep "DJANGO_SUPERUSER_PASSWORD=" "${FILE_}" | sed -e "s/^DJANGO_SUPERUSER_PASSWORD=//" )"
          break
        fi
      done
    fi
  fi

  if [[ -z ${DJANGO_SECRET_KEY} ]] || [[ -z ${DJANGO_SECRET_KEY} ]]; then
    echo -e "${ORANGE}""${BOLD}""Did not find saved passwords""${NC}"
    if [[ "$OS_TYPE" == "debian" ]]; then
      DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    elif [[ "$OS_TYPE" == "rhel" ]]; then
      DJANGO_SECRET_KEY=$(cd /var/www && python3.11 -m pipenv run python3.11 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    fi
    RANDOM_PW=$(openssl rand -base64 12)
  fi

  echo -e "${ORANGE}""${BOLD}""Creating a EMBArk configuration file .env""${NC}"
  {
    echo "DATABASE_NAME=embark"
    echo "DATABASE_USER=embark"
    echo "DATABASE_PASSWORD=${RANDOM_PW}"
    echo "DATABASE_HOST=172.22.0.5"
    echo "DATABASE_PORT=3306"
    echo "MYSQL_PASSWORD=${RANDOM_PW}"
    echo "MYSQL_USER=embark"
    echo "MYSQL_DATABASE=embark"
    echo "REDIS_HOST=172.22.0.8"
    echo "REDIS_PORT=7777"
    echo "SECRET_KEY=${DJANGO_SECRET_KEY}"
    echo "DJANGO_SUPERUSER_USERNAME=${SUPER_USER}"
    echo "DJANGO_SUPERUSER_EMAIL=${SUPER_EMAIL}"
    echo "DJANGO_SUPERUSER_PASSWORD=${SUPER_PW}"
    echo "PYTHONPATH=${PWD}:${PWD}/embark:/var/www/:/var/www/embark"
  } > .env
  chmod 600 .env
}

install_emba(){
  echo -e "\n${GREEN}""${BOLD}""Installation of the firmware scanner EMBA on host""${NC}"
  if git submodule status emba | grep --quiet '^-'; then
    sudo -u "${SUDO_USER:-${USER}}" git submodule init emba
  fi
  sudo -u "${SUDO_USER:-${USER}}" git submodule update --remote
  sudo -u "${SUDO_USER:-${USER}}" git config --global --add safe.directory "${PWD}"/emba
  cd emba
  ./installer.sh -d || ( echo "Could not install EMBA" && exit 1 )
  cd ..
  if ! (cd emba && ./emba -d 1); then
    echo -e "\n${RED}""${BOLD}""EMBA installation failed""${NC}"
    exit 1
  fi
  chown -R "${SUDO_USER:-${USER}}" emba
  echo -e "\n""--------------------------------------------------------------------""${NC}"
}

install_emba_src(){
  local TARBALL_URL_="https://github.com/e-m-b-a/emba/tarball/master/"

  echo -e "\n${GREEN}""${BOLD}""Installation of the firmware scanner EMBA on host""${NC}"
  if ! [[ -f ./emba/installer.sh ]]; then
    if [[ -n "${TARBALL_URL_}" ]]; then
      wget -O emba.tar.gz "${TARBALL_URL_}"
      # extract all but toplevel node into existing emba dir
      tar -xf emba.tar.gz -C emba --strip-components 1
    fi
  fi
  [[ -f ./emba/installer.sh ]] || ( echo "Could not install EMBA" && exit 1 )
  cd emba
  ./installer.sh -d || ( echo "Could not install EMBA" && exit 1 )
  cd ..
  if ! (cd emba && ./emba -d 1); then
    echo -e "\n${RED}""${BOLD}""EMBA installation failed""${NC}"
    exit 1
  fi
  chown -R "${SUDO_USER:-${USER}}" emba
  echo -e "\n""--------------------------------------------------------------------""${NC}"
}

create_ca (){
  # FIXME could use some work
  echo -e "\n${GREEN}""${BOLD}""Creating SSL Cert""${NC}"
  if ! [[ -d cert ]]; then
    sudo -u "${SUDO_USER:-${USER}}" git checkout -- cert
  fi
  cd cert || exit 1
  if [[ -f embark.local.csr ]] || [[ -f embark-ws.local.csr ]] || [[ -f embark.local.crt ]] || [[ -f embark-ws.local.crt ]]; then
    echo -e "\n${GREEN}""${BOLD}""Certs already generated, skipping""${NC}"
  else
    # create CA
    openssl genrsa -out rootCA.key 4096
    openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out rootCA.crt -subj '/CN=embark.local/O=EMBA/C=US'
    # create server sign requests (csr)
    openssl genrsa -out embark.local.key 2048
    openssl req -new -sha256 -key embark.local.key -out embark.local.csr  -subj '/CN=embark.local/O=EMBA/C=US'
    openssl genrsa -out embark-ws.local.key 2048
    openssl req -new -sha256 -key embark-ws.local.key -out embark-ws.local.csr  -subj '/CN=embark-ws.local/O=EMBA/C=US'
    # sign csr with ca
    openssl x509 -req -in embark.local.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out embark.local.crt -days 10000 -sha256
    openssl x509 -req -in embark-ws.local.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out embark-ws.local.crt -days 10000 -sha256
  fi
  cd .. || exit 1
}

dns_resolve(){
  echo -e "\n${GREEN}""${BOLD}""Install hostnames for local dns-resolve""${NC}"
  if ! grep -q "embark.local" /etc/hosts ; then
    printf "0.0.0.0     embark.local\n" >>/etc/hosts
  else
    echo -e "\n${ORANGE}""${BOLD}""hostname already in use!""${NC}"
  fi
}

reset_docker(){
  echo -e "\\n${GREEN}""${BOLD}""Reset EMBArk docker images""${NC}\\n"

  # EMBArk
  docker_image_rm "mysql" "latest"
  docker_image_rm "redis" "5"   # FIXME check newer version
  docker_network_rm "embark_backend"

  # EMBA
  if [[ "${REFORCE}" -eq 0 ]]; then
    docker_image_rm "embeddedanalyzer/emba" "latest"
  fi

  docker container prune -f --filter "label=flag" || true

}

install_deps(){
  if [[ "$OS_TYPE" == "debian" ]]; then
    echo -e "\n${GREEN}""${BOLD}""Install debian packages for EMBArk installation""${NC}"
    apt-get update -y
    # Git
    if ! command -v git > /dev/null ; then
      apt-get install -y git
    fi
    # Python3
    if ! command -v python3 > /dev/null ; then
      apt-get install -y python3
    fi
    # GCC
    if ! command -v gcc > /dev/null ; then
      apt-get install -y build-essential
    fi
    # Pip
    if ! command -v pip > /dev/null ; then
      apt-get install -y python3-pip
    fi
    # install pipenv
    if ! command -v pipenv > /dev/null ; then
      apt-get install -y pipenv
    fi
    # Docker + docker compose
    if [[ "${WSL}" -eq 1 ]]; then
      echo -e "\n${ORANGE}WARNING: If you are using WSL2, disable docker integration from the docker-desktop daemon!${NC}"
      read -p "Fix docker stuff, then continue. Press any key to continue ..." -n1 -s -r
    fi
    
    if command -v docker-compose > /dev/null ; then
      echo -e "\n${RED}""${BOLD}""Old docker-compose version found remove it please""${NC}"
      exit 1
    fi
    if ! command -v docker > /dev/null || ! command -v docker compose > /dev/null ; then
      if grep -q "VERSION_ID=\"24.04\"" /etc/os-release 2>/dev/null ; then
        apt-get install -y docker.io wmdocker docker-compose-plugin > /dev/null
      else
        # Add Docker's official GPG key:
        apt-get install -y ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc
        # Add the repository to Apt sources:
        # shellcheck source=/dev/null
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      fi
    fi
    # python3-dev
    if ! dpkg -l python3-dev &>/dev/null; then
      apt-get install -y python3-dev
    fi
    #  python3-django
    if ! dpkg -l python3-django &>/dev/null; then
      apt-get install -y python3-django
    fi
    # ansifilter
    if ! command -v ansifilter > /dev/null ; then
      apt-get install -y ansifilter
    fi
    # sshpass
    if ! command -v sshpass > /dev/null ; then
      apt-get install -y sshpass
    fi
    # in Ubuntu 22 the apt package is broken
    if ! pipenv --version ; then
      pip install --upgrade pipenv
    fi
  elif [[ "$OS_TYPE" == "rhel" ]]; then
    echo -e "\n${GREEN}""${BOLD}""Install rpm packages for EMBArk installation""${NC}"
    dnf install -y 'dnf-command(config-manager)' epel-release
    # Git
    if ! command -v git > /dev/null ; then
      dnf install -y git
    fi
    # Python3 & Pip
    if ! command -v python3.11 > /dev/null ; then
      dnf install -y python3.11
      alternatives --set python /usr/bin/python3.11
      alternatives --set python3 /usr/bin/python3.11
    fi
    if ! command -v pip3.11 > /dev/null ; then
      dnf install -y python3.11-pip
    fi
    # GCC / Build Tools
    if ! command -v gcc > /dev/null ; then
      dnf groupinstall -y "Development Tools"
    fi
    # install pipenv
    if ! command -v pipenv > /dev/null ; then
      pip3.11 install --upgrade pipenv
    fi
    # Docker + docker compose
    if [[ "${WSL}" -eq 1 ]]; then
      echo -e "\n${RED}WARNING: WSL with RHEL/Rocky is not supported!${NC}"
      exit 1
    fi
    if command -v docker-compose > /dev/null ; then
      echo -e "\n${RED}""${BOLD}""Old docker-compose version found remove it please""${NC}"
      exit 1
    fi
    if ! command -v docker > /dev/null || ! command -v docker compose > /dev/null ; then
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        dnf install -y --allowerasing docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        systemctl start docker
        systemctl enable docker
    fi
    # python3-devel
    dnf install -y python3.11-devel python3.11
    # ansifilter
    if ! command -v ansifilter > /dev/null ; then
      dnf install -y ansifilter
    fi
    # sshpass
    if ! command -v sshpass > /dev/null ; then
      dnf install -y sshpass
    fi
  else
    echo -e "\n${RED}""${BOLD}""Unsupported operating system: $ID""${NC}"
    exit 1
  fi
}

install_daemon(){
  echo -e "\n${GREEN}""${BOLD}""Install embark daemon""${NC}"
  sed -i "s|{\$EMBARK_ROOT_DIR}|${PWD}|g" embark.service
  if ! [[ -e /etc/systemd/system/embark.service ]] ; then
    cp "${PWD}"/embark.service /etc/systemd/system/embark.service
  fi
  systemctl daemon-reload
}

uninstall_daemon(){
  echo -e "\n${ORANGE}""${BOLD}""Uninstalling embark daemon""${NC}"
  if [[ -e /etc/systemd/system/embark.service ]] ; then
    systemctl stop embark.service
    systemctl disable embark.service
  fi
  sed -i "s|${PWD}|{\$EMBARK_ROOT_DIR}|g" embark.service
  systemctl daemon-reload
}

install_embark_default(){
  echo -e "\n${GREEN}""${BOLD}""Installation of the firmware scanning environment EMBArk""${NC}"

  if ! [[ -d /var/www ]]; then
    mkdir /var/www/
  fi
  if [[ "${WSL}" -eq 1 ]]; then
    echo -e "${RED}""${BOLD}""EMBArk currently does not support WSL in default mode. (only in Dev-mode)""${NC}"
  fi

  if [[ "$OS_TYPE" == "debian" ]]; then
    apt-get install -y -q default-libmysqlclient-dev build-essential mysql-client-core-8.0
  elif [[ "$OS_TYPE" == "rhel" ]]; then
    dnf module enable -y mysql:8.0
    dnf install -y mysql mysql-devel
    ln -s /usr/lib64/mysql/libmysqlclient.so /usr/lib64/libmysqlclient.so
    dnf install -y expat expat-devel
  fi

  #Add user for server
  if ! cut -d: -f1 /etc/passwd | grep -E www-embark ; then
    useradd www-embark -G wheel -c "embark-server-user" -M -r --shell=/usr/sbin/nologin -d /var/www/embark
  fi
  # emba nopw
  if ! grep 'www-embark ALL=(ALL) NOPASSWD:SETENV: /var/www/emba/emba' /etc/sudoers ; then
    echo 'www-embark ALL=(ALL) NOPASSWD:SETENV: /var/www/emba/emba' | EDITOR='tee -a' visudo
  fi
  # pkill nopw
  if ! grep 'www-embark ALL=(ALL) NOPASSWD: /bin/pkill' /etc/sudoers ; then
    echo 'www-embark ALL=(ALL) NOPASSWD: /bin/pkill' | EDITOR='tee -a' visudo
  fi

  #Server-Dir
  if ! [[ -d /var/www/media ]]; then
    mkdir /var/www/media
    touch /var/www/media/empty
  fi
  if ! [[ -d /var/www/media/log_zip ]]; then
    mkdir /var/www/media/log_zip
  fi
  if ! [[ -d /var/www/active ]]; then
    mkdir /var/www/active
  fi
  if ! [[ -d /var/www/emba_logs ]]; then
    mkdir /var/www/emba_logs
    echo "{}" > /var/www/emba_logs/empty.json
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
  echo -e "\n${GREEN}""${BOLD}""Install embark python environment""${NC}"
  cp ./Pipfile* /var/www/
  if [[ "$OS_TYPE" == "debian" ]]; then
    (cd /var/www && MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 pipenv install)
  elif [[ "$OS_TYPE" == "rhel" ]]; then
    # Pipenv not found because /usr/bin/local not in $PATH, call via python3 -m instead
    (cd /var/www && MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 python3.11 -m pipenv install --python $(which python3.11))
  fi

  # download externals
  if ! [[ -d ./embark/static/external ]]; then
    echo -e "\n${GREEN}""${BOLD}""Downloading of external files, e.g. jQuery, for the offline usability of EMBArk""${NC}"
    mkdir -p ./embark/static/external/{scripts,css}
    wget -O ./embark/static/external/scripts/jquery.js https://code.jquery.com/jquery-3.6.0.min.js
    wget -O ./embark/static/external/scripts/confirm.js https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js
    wget -O ./embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js
    wget -O ./embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js
    wget -O ./embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js
    wget -O ./embark/static/external/scripts/base64.js https://cdn.jsdelivr.net/npm/js-base64@3.7.5/+esm
    wget -O ./embark/static/external/scripts/ansi_up.js https://cdn.jsdelivr.net/npm/ansi_up@6.0.2/ansi_up.min.js
    wget -O ./embark/static/external/css/confirm.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css
    wget -O ./embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css
    wget -O ./embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css
    find ./embark/static/external/ -type f -exec sed -i '/sourceMappingURL/d' {} \;
  fi

  # write env-vars into ./.env
  write_env
  echo "EMBARK_INSTALL=deploy" >> ./.env

  if [[ "${WSL}" -eq 1 ]]; then
    check_docker_wsl
  fi

  # download images for container
  docker compose pull
  docker compose up -d

  # activate daemon
  systemctl start embark.service
  check_db
  docker compose stop
  echo -e "${GREEN}""${BOLD}""Ready to use \$sudo ./run-server.sh ""${NC}"
  echo -e "${GREEN}""${BOLD}""Which starts the server on (0.0.0.0) port 80 ""${NC}"
}

install_embark_dev(){
  echo -e "\n${GREEN}""${BOLD}""Building Development-Environment for EMBArk""${NC}"

  if [[ "$OS_TYPE" == "debian" ]]; then
    apt-get install -y npm pylint pycodestyle default-libmysqlclient-dev build-essential bandit yamllint mysql-client-core-8.0
    # apache2 apache2-dev
    # if ! command -v apache2 > /dev/null ; then
    #   apt-get install -y apache2 apache2-dev
    # fi
  elif [[ "$OS_TYPE" == "rhel" ]]; then
    dnf install -y npm bandit yamllint
    pip3 install pylint pycodestyle
    dnf module enable -y mysql:8.0
    dnf install -y mysql mysql-devel
    ln -s /usr/lib64/mysql/libmysqlclient.so /usr/lib64/libmysqlclient.so
  fi

  # get geckodriver
  if ! command -v geckodriver > /dev/null ; then
    wget https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz
    tar -xvf geckodriver-v0.33.0-linux64.tar.gz
    mv geckodriver  /usr/local/bin
    chmod +x /usr/local/bin/geckodriver
    rm geckodriver-v0.33.0-linux64.tar.gz
  fi
  # npm packages
  npm install -g jshint
  npm install -g @stoplight/spectral-cli
  # npm install -g dockerlinter

  # Add user nosudo
  echo "${SUDO_USER:-${USER}}"" ALL=(ALL) NOPASSWD:SETENV: ""${PWD}""/emba/emba" | EDITOR='tee -a' visudo
  echo "${SUDO_USER:-${USER}}"" ALL=(ALL) NOPASSWD: /bin/pkill" | EDITOR='tee -a' visudo
  echo "root ALL=(ALL) NOPASSWD:SETENV: ""${PWD}""/emba/emba" | EDITOR='tee -a' visudo
  echo "root ALL=(ALL) NOPASSWD: /bin/pkill" | EDITOR='tee -a' visudo

  # Set some globals
  echo "NO_UPDATE_CHECK=1" >> /etc/environment

  # pipenv
  echo -e "\n${GREEN}""${BOLD}""Install embark python environment""${NC}"
  if [[ "$OS_TYPE" == "debian" ]]; then
    MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 pipenv install --dev
  elif [[ "$OS_TYPE" == "rhel" ]]; then
    MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 python3.11 -m pipenv install --dev --python $(which python3.11)
  fi

  # Server-Dir
  if ! [[ -d media ]]; then
    mkdir media
    touch media/empty
    mkdir media/active
  fi
  if ! [[ -d media/log_zip ]]; then
    mkdir media/log_zip
  fi
  if ! [[ -d media ]]; then
    mkdir static
  fi
  if ! [[ -d mail ]]; then
    mkdir mail
  fi
  if ! [[ -d emba_logs ]]; then
    mkdir emba_logs
    echo "{}" > emba_logs/empty.json
  fi
  

  # download externals
  if ! [[ -d ./embark/static/external ]]; then
    echo -e "\n${GREEN}""${BOLD}""Downloading of external files, e.g. jQuery, for the offline usability of EMBArk""${NC}"
    mkdir -p ./embark/static/external/{scripts,css}
    wget -O ./embark/static/external/scripts/jquery.js https://code.jquery.com/jquery-3.6.0.min.js
    wget -O ./embark/static/external/scripts/confirm.js https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.js
    wget -O ./embark/static/external/scripts/bootstrap.js https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js
    wget -O ./embark/static/external/scripts/datatable.js https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.js
    wget -O ./embark/static/external/scripts/charts.js https://cdn.jsdelivr.net/npm/chart.js@3.5.1/dist/chart.min.js
    wget -O ./embark/static/external/scripts/base64.js https://cdn.jsdelivr.net/npm/js-base64@3.7.5/+esm
    wget -O ./embark/static/external/scripts/ansi_up.js https://cdn.jsdelivr.net/npm/ansi_up@6.0.2/ansi_up.min.js
    wget -O ./embark/static/external/css/confirm.css https://cdnjs.cloudflare.com/ajax/libs/jquery-confirm/3.3.2/jquery-confirm.min.css
    wget -O ./embark/static/external/css/bootstrap.css https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css
    wget -O ./embark/static/external/css/datatable.css https://cdn.datatables.net/v/bs5/dt-1.11.2/datatables.min.css
    find ./embark/static/external/ -type f -exec sed -i '/sourceMappingURL/d' {} \;
  fi

  # write env-vars into ./.env
  write_env
  echo "EMBARK_INSTALL=dev" >> ./.env
  chmod 644 .env

  # download images for container
  docker compose pull
  docker compose up -d

  check_db
  docker compose stop
  echo -e "${GREEN}""${BOLD}""Ready to use \$sudo ./dev-tools/debug-server-start.sh""${NC}"
  echo -e "${GREEN}""${BOLD}""Or use otherwise""${NC}"
}

uninstall(){
  echo -e "[+]${CYAN}""${BOLD}""Uninstalling EMBArk""${NC}"

  if [[ "${NO_GIT}" -eq 0 ]]; then
    # check for changes
    if [[ $(git status --porcelain --untracked-files=no --ignore-submodules=all) ]]; then
      # Changes
      echo -e "[!!]${RED}""${BOLD}""Changes detected - please stash or commit them ${ORANGE}( \$git stash )""${NC}"
      git status
      exit 1
    fi
  fi

  # delete directories
  echo -e "${ORANGE}""${BOLD}""Delete Directories""${NC}"
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
  if [[ -d ./embark/static/external ]]; then
    rm -Rv ./embark/static/external
  fi
  if [[ -d ./cert ]]; then
    rm -Rv ./cert
  fi
  if [[ -d ./.venv ]]; then
    rm -Rvf ./.venv
  fi
  if [[ -d ./logs ]]; then
    rm -Rvf ./logs
  fi
  if [[ "${REFORCE}" -eq 0 ]]; then
    # user-files
    if [[ -d ./emba_logs ]]; then
      echo -e "${RED}""${BOLD}""Do you wish to remove the EMBA-Logs (and backups)""${NC}"
      rm -RIv ./emba_logs
    fi
    if [[ -d ./embark_db ]]; then
      echo -e "${RED}""${BOLD}""Do you wish to remove the database(and backups)""${NC}"
      rm -RIv ./embark_db
      if [[ -f ./safe/history.env ]]; then
        echo -e "${RED}""${BOLD}""Moved old history file""${NC}"
        mv --force ./safe/history.env ./safe/old_env_history
      fi
    fi
  fi

  # delete user www-embark and reset visudo
  echo -e "${ORANGE}""${BOLD}""Delete user""${NC}"

  if id -u www-embark &>/dev/null ; then
    userdel www-embark
  fi

  # remove all emba/embark NOPASSWD entries into sudoer file
  if grep -qE "NOPASSWD\:.*\/emba\/emba" /etc/sudoers ; then
    echo -e "${ORANGE}""${BOLD}""Deleting EMBA NOPASSWD entries""${NC}"
    sed -i '/NOPASSWD\:.*\/emba\/emba/d' /etc/sudoers
  fi
  if grep -qE "NOPASSWD\:.*\/bin\/pkill" /etc/sudoers ; then
    echo -e "${ORANGE}""${BOLD}""Deleting pkill NOPASSWD entries""${NC}"
    sed -i '/NOPASSWD\:.*\/bin\/pkill/d' /etc/sudoers
  fi

  # delete .env
  echo -e "${ORANGE}""${BOLD}""Delete env""${NC}"
  if [[ -f ./.env ]]; then
    rm -Rvf ./.env
  fi

  # delete shared volumes and migrations
  echo -e "${ORANGE}""${BOLD}""Delete migration-files""${NC}"
  find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
  find . -path "*/migrations/*.pyc"  -delete

  # delete all docker interfaces and containers + images
  reset_docker
  echo -e "${ORANGE}""${BOLD}""Consider running " "${CYAN}""\$docker system prune""${NC}"
  
  # emba
  if [[ -d ./emba/external ]]; then
    rm -r ./emba/external/
  fi
  if [[ "${NO_GIT}" -eq 1 && "${REFORCE}" -eq 0 ]]; then
    # simple delete emba
    rm -RIv ./emba
  else
    # delete/uninstall submodules
    if [[ "${REFORCE}" -eq 1 ]]; then
      sudo -u "${SUDO_USER:-${USER}}" git submodule status
    else
      if [[ $(sudo -u "${SUDO_USER:-${USER}}" git submodule foreach git status --porcelain --untracked-files=no) ]]; then
        echo -e "[!!]${RED}""${BOLD}""Submodule changes detected - please commit them...otherwise they will be lost""${NC}"
        read -p "If you know what you are doing you can press any key to continue ..." -n1 -s -r
      fi
      sudo -u "${SUDO_USER:-${USER}}" git submodule foreach git reset --hard
      sudo -u "${SUDO_USER:-${USER}}" git submodule foreach git clean -f -x
      sudo -u "${SUDO_USER:-${USER}}" git submodule deinit --all -f
    fi
  fi

  # stop&reset daemon
  if [[ "${WSL}" -ne 1 ]]; then
    uninstall_daemon
    systemctl daemon-reload
  fi

  # reset server-certs
  rm -RIv ./cert/*

  # final
  if [[ "${REFORCE}" -eq 0 ]]; then
    rm -r ./safe
  fi
  if [[ "${NO_GIT}" -eq 0 ]]; then
    sudo -u "${SUDO_USER:-${USER}}" git checkout HEAD -- embark.service
    sudo -u "${SUDO_USER:-${USER}}" git checkout HEAD -- cert
    sudo -u "${SUDO_USER:-${USER}}" git reset
    echo -e "${ORANGE}""${BOLD}""Consider ""${CYAN}""\$git pull""${ORANGE}""${BOLD}"" and ""${CYAN}""\$git clean""${NC}"
  else
    echo -e "${ORANGE}""${BOLD}""Consider removing this directory manually""${NC}"
  fi
}

echo -e "\\n${ORANGE}""${BOLD}""EMBArk Installer""${NC}\\n""${BOLD}=================================================================${NC}"
echo -e "${ORANGE}""${BOLD}""WARNING: This script can harm your environment!""${NC}\n"

import_helper

if [[ "${STRICT_MODE}" -eq 1 ]]; then
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
  echo -e "${RED}""${BOLD}""Invalid number of arguments""${NC}"
  print_help
  exit 1
fi

while getopts esFUrdDSh OPT ; do
  case ${OPT} in
    e)
      export EMBA_ONLY=1
      echo -e "${GREEN}""${BOLD}""Install only emba""${NC}"
      ;;
    s)
      export NO_EMBA=1
      echo -e "${GREEN}""${BOLD}""Install without emba""${NC}"
      ;;
    F)
      export DEV=1
      echo -e "${GREEN}""${BOLD}""Building Development-Enviroment""${NC}"
      ;;
    U)
      export UNINSTALL=1
      echo -e "${GREEN}""${BOLD}""Uninstall EMBArk""${NC}"
      ;;
    r)
      export UNINSTALL=1
      export REFORCE=1
      echo -e "${GREEN}""${BOLD}""Re-Install all dependencies while keeping user-files""${NC}"
      ;;
    d)
      export DEFAULT=1
      echo -e "${GREEN}""${BOLD}""Default installation of EMBArk""${NC}"
      ;;
    S)
      export STRICT_MODE=1
      echo -e "${GREEN}""${BOLD}""Strict-mode enabled""${NC}"
      ;;
    h)
      print_help
      exit 0
      ;;
    *)
      echo -e "${RED}""${BOLD}""Invalid option""${NC}"
      print_help
      exit 1
      ;;
  esac
done

enable_strict_mode ${STRICT_MODE}

# WSL/OS version check
# WSL support - currently experimental!
if grep -q -i wsl /proc/version; then
  echo -e "\n${ORANGE}INFO: System running in WSL environment!${NC}"
  echo -e "\n${ORANGE}INFO: WSL is currently experimental!${NC}"
  echo -e "\n${ORANGE}INFO: Ubuntu 22.04 is required for WSL!${NC}"
  read -p "If you know what you are doing you can press any key to continue ..." -n1 -s -r
  WSL=1
fi

if [[ ${EUID} -ne 0 ]]; then
  echo -e "\\n${RED}""Run EMBArk installation script with root permissions!""${NC}\\n"
  print_help
  exit 1
fi

OS_ID=$(source /etc/os-release; echo "$ID")
if [[ "$OS_ID" == "ubuntu" ]] || [[ "$OS_ID" == "kali" ]] || [[ "$OS_ID" == "debian" ]]; then
  OS_TYPE="debian"
elif [[ "$OS_ID" == "rhel" ]] || [[ "$OS_ID" == "rocky" ]] || [[ "$OS_ID" == "centos" ]] || [[ "$OS_ID" == "fedora" ]]; then
  OS_TYPE="rhel"
fi

if ! [[ -d .git ]]; then
  export NO_GIT=1
fi

if [[ ${REFORCE} -eq 1 ]] && [[ ${UNINSTALL} -eq 1 ]]; then
  save_old_env
  uninstall
elif [[ ${UNINSTALL} -eq 1 ]]; then
  save_old_env
  uninstall
  exit 0
fi

install_deps

# mark dir as safe for git
sudo -u "${SUDO_USER:-${USER}}" git config --global --add safe.directory "${PWD}"


if [[ "${NO_EMBA}" -eq 0 ]]; then
  if [[ "${NO_GIT}" -eq 1 ]]; then
    install_emba_src
  else
    install_emba
  fi
fi

if [[ "${EMBA_ONLY}" -eq 0 ]]; then
  if [[ ${DEFAULT} -eq 1 ]]; then
    install_embark_default
  elif [[ ${DEV} -eq 1 ]]; then
    install_embark_dev
  fi
fi

if [[ "${NO_GIT}" -eq 1 ]]; then
  echo "EMBA_INSTALL=src" >> .env
elif [[ "${NO_EMBA}" -eq 1 ]]; then
  echo "EMBA_INSTALL=no" >> .env
else
  echo "EMBA_INSTALL=git" >> .env
fi

exit 0
