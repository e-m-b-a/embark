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

# Description: Automates import of db file for quick transfer between systems and general usability

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

ALT_BACKUP_FILE="${1:-}"
export BACKUP_FILE=""
if [[ -n "${ALT_BACKUP_FILE}" ]]; then
  if ! [[ -f "${ALT_BACKUP_FILE}" ]]; then
    echo -e "\\n${RED}""Error with input for BACKUP FILE!""${NC}\\n"
    exit 1
  fi
  BACKUP_FILE="${ALT_BACKUP_FILE}"
else
  BACKUP_FILE="$(find . -type f -iname "full-backup-*.tar" | sort -n | tail -n 1)"
fi

cd "$(dirname "${0}")" || exit 1

if ! [[ ${EUID} -eq 0 ]] ; then
  echo -e "\\n${RED}""Run script with root permissions!""${NC}\\n"
  exit 1
fi

echo "USER is ${SUDO_USER:-${USER}}"

import_helper

tar -xf "${BACKUP_FILE}"

rsync -a --progress ./.embark_db_backup/ ./embark_db/

rm -rf ./.embark_db_backup/

echo -e "\\n""==> ""${GREEN}""Import successful""${NC}"
