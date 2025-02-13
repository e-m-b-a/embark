#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2025 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Automates export of db files for quick transfer between systems and general backup

export WSL=0

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export ORANGE='\033[0;33m'
export BLUE='\033[0;34m'
export BOLD='\033[1m'
export NC='\033[0m' # no color

import_helper()
{
  local HELPERS=()
  local HELPER_COUNT=0
  local HELPER_FILE=""
  local HELP_DIR='helper'
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


cd "$(dirname "${0}")" || exit 1

if ! [[ ${EUID} -eq 0 ]] ; then
  echo -e "\\n${RED}""Run script with root permissions!""${NC}\\n"
  exit 1
fi

echo "USER is ${SUDO_USER:-${USER}}"

import_helper
cp -urvi ./embark_db ./.embark_db_backup
tar -cf full-backup-"$(date +%F)".tar ./.embark_db_backup
