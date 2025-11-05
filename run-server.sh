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
# Author(s): Benedikt Kuehne
# Contributor(s): ClProsser, ashiven, SirGankalot

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
export ADMIN_HOST_RANGE=()
export EMBARK_BASEDIR=""
export OS_TYPE=""

STRICT_MODE=0
EMBARK_BASEDIR="$(realpath "$(dirname "${0}")")"

CELERY_PID=0
PIPENV_CHANGED=0

import_helper()
{
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

cleaner() {
  # stops ALL emba processes started from within embark that were not killed successfully
  # timeout 30s pkill -u root -f "embark/emba/emba"
  local PID_FILES=()
  mapfile -d '' PID_FILES < <(find "${EMBA_LOG_ROOT:-emba_logs}" -type f -name "emba_run.pid" -print0 2> /dev/null)

  if [[ ${#PID_FILES[@]} -ne 0 ]]; then
    for FILE in "${PID_FILES[@]}"; do
      echo -e "${RED}""${BOLD}""Making sure the EMBA process with PID ""$(cat "${FILE}")"" from ""${FILE}"" is stopped""${NC}"
      timeout 3s pkill -F "${FILE}"
    done
  fi

  timeout 30s pkill -u root -f "runapscheduler"

  if [ ${CELERY_PID} -ne 0 ]; then
    timeout 10s kill --timeout 5000 KILL ${CELERY_PID} 2>/dev/null
  fi

  timeout 5s fuser -k "${HTTP_PORT}"/tcp
  timeout 5s fuser -k "${HTTPS_PORT}"/tcp
  timeout 5s fuser -k 8000/tcp
  timeout 5s fuser -k 8001/tcp

  timeout 10s docker container stop embark_db
  timeout 10s docker container stop embark_redis

  sync_emba_backward || echo -e "${RED}""${BOLD}""Syncing EMBA backward failed!""${NC}"
  systemctl stop embark.service
  exit 0
}

# main
echo -e "\\n${ORANGE}""${BOLD}""EMBArk Startup""${NC}\\n""${BOLD}=================================================================${NC}"

while getopts "ha:b:i:" OPT ; do
  case ${OPT} in
    h)
      echo -e "\\n""${CYAN}""USAGE""${NC}"
      echo -e "${CYAN}-h${NC}           Print this help message"
      echo -e "${CYAN}-a <IP/Name>${NC} Add a server Virtualhost alias"
      echo -e "${CYAN}-b <IP/Range>${NC} Add a ipv4 to access the admin pages from"
      echo -e "${CYAN}-i <IP>${NC} specify the ipv4 to host the server on (default=0.0.0.0)"
      echo -e "---------------------------------------------------------------------------"
      if ip addr show eth0 &>/dev/null ; then
        IP=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
      elif ip -4 a show scope 0 &>/dev/null ; then
        IP=$(ip -4 a show scope 0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1 | head -n 1)
      fi
      if [[ -n "${IP}" ]]; then
        echo -e "${GREEN} Suggestion:${NC}  sudo ./run-server.sh -a ${IP} -b ${IP}/24""\n"
        echo -e "${GREEN} nslookup helper:${NC}"
        nslookup -timeout=1 "${IP}"
      fi
      exit 0
      ;;
    a)
      SERVER_ALIAS+=("${OPTARG}")
      WSGI_FLAGS+=(--server-alias "${OPTARG}")
      ;;
    b)
      ADMIN_HOST_RANGE+=("${OPTARG}")
      ;;
    i)
      BIND_IP="${OPTARG}"
      echo -e "${GREEN} Bind IP set to: ${BIND_IP}""${NC}"
      ;;
    :)
      echo -e "${CYAN} Usage: [-a <IP/HOSTNAME>] [-b <IP/Range>] [-i <IP>] ${NC}"
      exit 1
      ;;
    *)
      echo -e "\\n${ORANGE}""${BOLD}""No Alias set""${NC}\\n"
      ;;
  esac
done

# Bind IP check
if ! [[ ${BIND_IP} == "0.0.0.0" ]]; then

  # localhost to loopback for sanitization
  if [[ ${BIND_IP} == "localhost" ]]; then
    BIND_IP="127.0.0.1"
  fi
  #sanitize IP
  if ! [[ ${BIND_IP} =~ ^((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$ ]] ; then
    echo -e "\\n${RED}""${BOLD}""The bind IP (${BIND_IP}) is not a valid IPv4 address!""${NC}\\n"
    exit 1
  fi
  # check if IP is configured on host
  if ! ip addr show | grep -q "${BIND_IP}"; then
    echo -e "\\n${RED}""${BOLD}""The bind IP (${BIND_IP}) is not configured on this host!""${NC}\\n"
    exit 1
  fi

fi

# add to hosts file with correct IP
sed -i "/embark.local/d" /etc/hosts
echo -e "${BIND_IP}     embark.local\\n" >>/etc/hosts


# Alias
if [[ ${#SERVER_ALIAS[@]} -ne 0 ]]; then
  echo -e "${GREEN} Server-alias:${NC}"
  for VAR in "${SERVER_ALIAS[@]}"; do
    echo "[*] ${VAR}"
  done
fi

# shellcheck disable=SC1091 # No need to validate /etc/os-release
lOS_ID=$(source /etc/os-release; echo "${ID}")
if [[ "${lOS_ID}" == "ubuntu" ]] || [[ "${lOS_ID}" == "kali" ]] || [[ "${lOS_ID}" == "debian" ]]; then
  OS_TYPE="debian"
elif [[ "${lOS_ID}" == "rhel" ]] || [[ "${lOS_ID}" == "rocky" ]] || [[ "${lOS_ID}" == "centos" ]] || [[ "${lOS_ID}" == "fedora" ]]; then
  OS_TYPE="rhel"
fi

PIPENV_COMMAND="pipenv"
if [[ "${OS_TYPE}" == "rhel" ]]; then
  PIPENV_COMMAND="$(which python3.11) -m pipenv"
fi

cd "${EMBARK_BASEDIR}" || exit 1
import_helper
enable_strict_mode "${STRICT_MODE}"
set -a
trap cleaner INT

if ! [[ ${EUID} -eq 0 ]] ; then
  echo -e "\\n${RED}""Run Server script with root permissions!""${NC}\\n"
  exit 1
fi

# start container first (speedup?)
docker compose -f ./docker-compose.yml up -d

# check emba
echo -e "${BLUE}""${BOLD}""checking EMBA""${NC}"
if ! [[ -d ./emba ]]; then
  echo -e "${RED}""${BOLD}""You are using the wrong installation and missing the EMBA subdirectory""${NC}"
fi
if ! (cd "${EMBARK_BASEDIR:-${PWD}}"/emba && ./emba -d 1); then
  echo -e "${RED}""EMBA is not configured correctly""${NC}"
  exit 1
fi

# check disk-size
echo -e "${BLUE}""${BOLD}""Checking disk size""${NC}"
AVAILABLE_SIZE="$(df -l /var/www/ | awk '{print $4}' | grep -E '^[0-9]+$')"
echo -e "${GREEN}""Available disk size: ${AVAILABLE_SIZE} KB""${NC}"
if [[ "${AVAILABLE_SIZE}" -lt 4000000 ]]; then
  echo -e "${RED}""Less than 4GB disk space available for the Server!""${NC}"
  exit 1
fi

# check venv
if ! [[ -d /var/www/.venv ]]; then
  echo -e "${RED}""${BOLD}""Pip-enviroment not found!""${NC}"
  exit 1
fi

# sync pipfile
if [[ -n "$(rsync -r -u --progress --chown="${SUDO_USER}" "${EMBARK_BASEDIR}"/Pipfile* /var/www/)" ]]; then
  # update if changes
  PIPENV_CHANGED=1
fi



if ! nc -zw1 pypi.org 443 &>/dev/null ; then
  if ! (cd /var/www && "${PIPENV_COMMAND}" verify) ; then
    (cd /var/www && MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 "${PIPENV_COMMAND}" update)
  fi
  (cd /var/www && "${PIPENV_COMMAND}" check)
fi

# check db and start container
check_db

# update cves
if [[ -d ./emba/external/nvd-json-data-feeds ]]; then
  (cd ./emba/external/nvd-json-data-feeds && git pull)
fi

# sync emba
sync_emba_forward

# logs
if ! [[ -d ./docker_logs ]]; then
  mkdir docker_logs
fi

# container-logs (2 jobs)
echo -e "\n[""${BLUE} JOB""${NC}""] Redis logs are copied to ./docker_logs/redis.log"
docker container logs embark_redis -f &> ./docker_logs/redis.log &
echo -e "\n[""${BLUE} JOB""${NC}""] DB logs are copied to ./embark/logs/mysql.log"
docker container logs embark_db -f &> ./docker_logs/mysql.log &

# start the supervisor
systemctl enable embark.service
systemctl start embark.service

# copy django server
rsync -r -u --progress --chown=www-embark:sudo ./embark/ /var/www/embark/

# config apache
# add all modules we want (mod_ssl mod_auth_basic etc)
# post_max_size increase
if ! [[ -d /var/www/conf ]]; then
  mkdir /var/www/conf
fi
{
  echo -e "LoadModule auth_basic_module \${MOD_WSGI_MODULES_DIRECTORY}/mod_auth_basic.so"
  echo -e "LoadModule authz_user_module \${MOD_WSGI_MODULES_DIRECTORY}/mod_authz_user.so"
  echo -e "WSGIPythonHome /var/www/.venv"
  echo -e "WSGIPythonPath /var/www/embark/embark"
  echo -e ""
  echo -e "WSGIProcessGroup %{GLOBAL}"
  echo -e "WSGIApplicationGroup %{GLOBAL}"
  echo -e ""
  echo -e "<Location /admin>"
  echo -e "<IfVersion < 2.4>"
  echo -e "  Order deny,allow"
  echo -e "  Deny from all"
  echo -e "  Allow from 127.0.0.1"
  if [[ ${#ADMIN_HOST_RANGE[@]} -ne 0 ]]; then
    echo -e "  Allow from ${ADMIN_HOST_RANGE[*]}"
  fi
  echo -e "</IfVersion>"
  echo -e "<IfVersion >= 2.4>"
  echo -e "    Require all granted"
  echo -e "    Require ip 127.0.0.1"
  if [[ ${#ADMIN_HOST_RANGE[@]} -ne 0 ]]; then
    echo -e "    Require ip ${ADMIN_HOST_RANGE[*]}"
  fi
  echo -e "</IfVersion>"
  echo -e "</Location>"
  echo -e ""
  echo -e "Alias '/media' '/var/www/media'"
  echo -e "<Location /media>"
  echo -e "<IfVersion < 2.4>"
  echo -e "  Order deny,allow"
  echo -e "  Deny from all"
  echo -e "  Allow from 127.0.0.1"
  if [[ ${#ADMIN_HOST_RANGE[@]} -ne 0 ]]; then
    echo -e "  Allow from ${ADMIN_HOST_RANGE[*]}"
  fi
  echo -e "  AuthType Basic"
  echo -e "  AuthName Admin"
  echo -e "  AuthBasicProvider wsgi"
  echo -e "  WSGIAuthUserScript /var/www/embark/embark/wsgi_auth.py"
  echo -e "  WSGIAuthGroupScript /var/www/embark/embark/wsgi_auth.py"
  # echo -e "  Require valid-user"
  echo -e "  Require wsgi-group Administration_Group"
  echo -e "</IfVersion>"
  echo -e "<IfVersion >= 2.4>"
  echo -e "  Require all granted"
  echo -e "  Require ip 127.0.0.1"
  if [[ ${#ADMIN_HOST_RANGE[@]} -ne 0 ]]; then
    echo -e "  Require ip ${ADMIN_HOST_RANGE[*]}"
  fi
  echo -e "  AuthType Basic"
  echo -e "  AuthName Admin"
  echo -e "  AuthBasicProvider wsgi"
  echo -e "  WSGIAuthUserScript /var/www/embark/embark/wsgi_auth.py"
  echo -e "  WSGIAuthGroupScript /var/www/embark/embark/wsgi_auth.py"
  # echo -e "  Require valid-user"
  echo -e "  Require wsgi-group Administration_Group"
  echo -e "</IfVersion>"
  echo -e "</Location>"
  # echo -e "<Directory /var/www/embark/embark>"
  # echo -e "  <Files wsgi_auth.py>"
  # echo -e "    Require all granted"
  # echo -e "  </Files>"
  # echo -e "</Directory>"
} > /var/www/conf/embark.conf

# certs
if ! [[ -d /var/www/conf/cert ]]; then
  mkdir /var/www/conf/cert
fi
copy_file "${EMBARK_BASEDIR:-${PWD}}"/cert/embark.local.crt /var/www/conf/cert
copy_file "${EMBARK_BASEDIR:-${PWD}}"/cert/embark.local.key /var/www/conf/cert
copy_file "${EMBARK_BASEDIR:-${PWD}}"/cert/embark-ws.local.key /var/www/conf/cert
copy_file "${EMBARK_BASEDIR:-${PWD}}"/cert/embark-ws.local.crt /var/www/conf/cert


# cp .env and version
copy_file ./.env /var/www/embark/embark/settings/   # security-- # TODO
copy_file ./VERSION.txt /var/www/embark/

# !DIRECTORY-CHANGE!
cd /var/www/embark/ || exit 1

# start venv (ignore source in script)
# shellcheck disable=SC1091
source /var/www/.venv/bin/activate || exit 1
export PIPENV_VERBOSITY=-1

if [[ "${PIPENV_CHANGED}" -eq 1]]; then
  "${PIPENV_COMMAND}" update
fi

# logs
if ! [[ -d /var/www/logs ]]; then
  mkdir /var/www/logs
fi

# db_init
echo -e "\n[""${BLUE} JOB""${NC}""] Starting migrations - log to embark/logs/migration.log"
"${PIPENV_COMMAND}" run ./manage.py makemigrations | tee -a /var/www/logs/migration.log
"${PIPENV_COMMAND}" run ./manage.py migrate | tee -a /var/www/logs/migration.log

# collect staticfiles and make accesable for server
echo -e "\n[""${BLUE} JOB""${NC}""] Collecting static files"
"${PIPENV_COMMAND}" run ./manage.py collectstatic --no-input
chown www-embark /var/www/ -R
chmod 760 /var/www/media/ -R

echo -e "\n[""${BLUE} JOB""${NC}""] Starting runapscheduler"
"${PIPENV_COMMAND}" run ./manage.py runapscheduler | tee -a /var/www/logs/scheduler.log &
sleep 5

# create admin superuser
echo -e "\n[""${BLUE} JOB""${NC}""] Creating Admin account"
"${PIPENV_COMMAND}" run ./manage.py createsuperuser --noinput 2>/dev/null

# load default groups
echo -e "\n[""${BLUE} JOB""${NC}""] Creating default permission groups"
"${PIPENV_COMMAND}" run ./manage.py loaddata ./*/fixtures/*.json 2>/dev/null

echo -e "\n[""${BLUE} JOB""${NC}""] Starting Apache"
"${PIPENV_COMMAND}" run ./manage.py runmodwsgi --user www-embark --group sudo \
--host "${BIND_IP}" --port="${HTTP_PORT}" --limit-request-body "${FILE_SIZE}" \
--url-alias /static/ /var/www/static/ \
--url-alias /media/ /var/www/media/ \
--allow-localhost --working-directory /var/www/embark/ --server-root /var/www/httpd80/ \
--include-file /var/www/conf/embark.conf \
--processes 4 --threads 4 \
--graceful-timeout 5 \
--log-level debug \
--server-name "embark.local" \
--server-alias localhost \
--server-alias "${BIND_IP}" "${WSGI_FLAGS[@]}" &
# --ssl-certificate /var/www/conf/cert/embark.local --ssl-certificate-key-file /var/www/conf/cert/embark.local.key \
# --https-port "${HTTPS_PORT}" &
#  --https-only --enable-debugger \
sleep 5

echo -e "\n[""${BLUE} JOB""${NC}""] Starting daphne(ASGI) - log to /embark/logs/daphne.log"
cd /var/www/embark && sudo -u www-embark "${PIPENV_COMMAND}" run daphne --access-log /var/www/logs/daphne.log -e ssl:8000:privateKey=/var/www/conf/cert/embark-ws.local.key:certKey=/var/www/conf/cert/embark-ws.local.crt -b "${BIND_IP}" -p 8001 -s embark-ws.local embark.asgi:application &
sleep 5

# Start celery worker
sudo -u www-embark "${PIPENV_COMMAND}" run python -m celery -A embark worker --beat --scheduler django -l INFO --logfile=../logs/celery.log &
CELERY_PID=$!

echo -e "\n""${ORANGE}${BOLD}""=============================================================""${NC}"
echo -e "\n""${ORANGE}${BOLD}""EMBA logs are under /var/www/emba_logs/<id> ""${NC}"
# echo -e "\n\n""${GREEN}${BOLD}""the trusted rootCA.key for the ssl encryption is in ./cert""${NC}"
if [[ ${#SERVER_ALIAS[@]} -ne 0 ]]; then
  echo -e "\n""${ORANGE}${BOLD}""Server started on http://embark.local with aliases:""${NC}"
  for _alias in "${!SERVER_ALIAS[@]}" ; do
    echo -e "\n${ORANGE}http://${SERVER_ALIAS["${_alias}"]}:${HTTP_PORT}${NC}"
  done
else
  echo -e "\n""${ORANGE}${BOLD}""Server started on http://embark.local"":""${HTTP_PORT}""${NC}"
fi
# echo -e "\n""${ORANGE}${BOLD}""For SSL you may use https://embark.local (Not recommended for local use)""${NC}"
wait
