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

# Description: Miscellaneous helper functions

docker_image_rm(){
  # removes image by name and version
  # $1 name
  # $2 version
  local IMAGE_NAME_="${1:-}"
  local IMAGE_VERSION_="${2:-}"

  if [[ $(docker image ls -q "$IMAGE_NAME_"":""$IMAGE_VERSION_" | wc -c ) -ne 0 ]] ; then
    if [[ $(docker ps -a -q --filter "ancestor=""$IMAGE_NAME_"":""$IMAGE_VERSION_" | wc -c) -ne 0 ]]; then
      local CONTAINERS_
      mapfile -t CONTAINERS_ < <(docker ps -a -q --filter ancestor="$IMAGE_NAME_"":""$IMAGE_VERSION_" --format="{{.ID}}")
      for CONTAINER_ID_ in "${CONTAINERS_[@]}" ; do
        echo -e "$GREEN""$BOLD""Stopping ""$CONTAINER_ID_"" docker container""$NC"
        docker stop "$CONTAINER_ID_"
        echo -e "$GREEN""$BOLD""Remove ""$CONTAINER_ID_"" docker container""$NC"
        docker container rm "$CONTAINER_ID_" -f
      done
    fi
    echo -e "$GREEN$BOLD""Removing ""$IMAGE_NAME_"":""$IMAGE_VERSION_" "docker image""$NC\\n"
    docker image rm "$IMAGE_NAME_"":""$IMAGE_VERSION_" -f
  fi
}

docker_network_rm(){
  # removes docker networks by name
  local NET_NAME="${1:-}"
  local NET_ID=""
  if docker network ls | grep -E "$NET_NAME"; then
    echo -e "\n$GREEN""$BOLD""Found ""$NET_NAME"" - removing it""$NC"
    NET_ID=$(docker network ls | grep -E "$NET_NAME" | awk '{print $1}')
    echo -e "$GREEN""$BOLD""Remove ""$NET_NAME"" network""$NC"
    docker network rm "$NET_ID" 
  fi
}

copy_file(){
  # check and copy file forcing overwrite
  local SOURCE_="${1:-}"
  local DESTINATION_="${2:-}"
  if ! [[ -f "$SOURCE_" ]] ; then
    echo -e "\\n$RED""Could not find ""$SOURCE_""$NC\\n"
    return 1
  elif  ! [[ -d $(dirname "$DESTINATION_") ]] ; then
    echo -e "\\n$RED""Could not find ""$DESTINATION_""$NC\\n"
    return 1
  fi
  cp -f "$SOURCE_" "$DESTINATION_"
}

enable_strict_mode() {
  local STRICT_MODE_="${1:-}"

  if [[ "$STRICT_MODE_" -eq 1 ]]; then
    # http://redsymbol.net/articles/unofficial-bash-strict-mode/
    # https://github.com/tests-always-included/wick/blob/master/doc/bash-strict-mode.md
    # shellcheck disable=SC1091
    source ./helper/wickStrictModeFail.sh
    set -e          # Exit immediately if a command exits with a non-zero status
    set -u          # Exit and trigger the ERR trap when accessing an unset variable
    set -o pipefail # The return value of a pipeline is the value of the last (rightmost) command to exit with a non-zero status
    set -E          # The ERR trap is inherited by shell functions, command substitutions and commands in subshells
    shopt -s extdebug # Enable extended debugging
    IFS=$'\n\t'     # Set the "internal field separator"
    trap 'wickStrictModeFail $? | tee -a /tmp/embark_error.log' ERR  # The ERR trap is triggered when a script catches an error

    echo -e "[!] INFO: EMBArk STRICT mode enabled!"

  fi
}

check_docker_wsl() {
  # checks if service docker is running
  echo -e "$BLUE""$BOLD""checking docker""$NC\\n"
  service docker status
}

check_db() {
  local PW_ENV
  local USER_ENV
  local HOST_ENV
  PW_ENV=$(grep DATABASE_PASSWORD ./.env | sed 's/DATABASE\_PASSWORD\=//')
  USER_ENV=$(grep DATABASE_USER ./.env | sed 's/DATABASE\_USER\=//')
  HOST_ENV=$(grep DATABASE_HOST ./.env | sed 's/DATABASE\_HOST\=//')
  echo -e "\\n$ORANGE""$BOLD""checking database""$NC\\n""$BOLD=================================================================$NC"
  echo -e "$BLUE""$BOLD""1. checking startup""$NC\\n"
  if docker-compose -f ./docker-compose.yml up -d ; then
    echo -e "$GREEN""$BOLD""Finished setup mysql and redis docker images""$NC"
  else
    echo -e "$ORANGE""$BOLD""Failed setup mysql and redis docker images""$NC"
    exit 1
  fi
  echo -e "$BLUE""$BOLD""2. checking password""$NC\\n"
  if ! mysql --host="$HOST_ENV" --user="$USER_ENV" --password="$PW_ENV" -e"quit"; then  # PW_ENV=$(grep DATABASE_PASSWORD ./.env | sed 's/DATABASE\_PASSWORD\=//')mysql -h 172.22.0.5 -u embark -p $PW_ENV -e "quit"
    echo -e "$ORANGE""$BOLD""Failed logging into database with password""$NC"
    echo -e "---------------------------------------------------------------------------"
    echo -e "$CYAN""Old passwords are stored in the \"safe\" folder when uninstalling EMBArk""$NC\\n"
    echo -e "$CYAN""You could try recoverying manually by overwriting your\".env\" file""$NC\\n"
    exit 1
  fi
}

check_safe() {
  local ENV_FILES=()
  if [[ -d safe ]] ; then
    mapfile -d '' ENV_FILES < <(find ./safe -iname "*.env" -print0 2> /dev/null)
    if [ ${#ENV_FILES[@]} -gt 0 ]; then
      return 1
    fi
  fi
  return 0
}
