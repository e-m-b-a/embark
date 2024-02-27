#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2024 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Helper script to get our Copyright things in order

YEAR=2024

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color


EXCEPTIONS_TO_CHECK_ARR=()

write_headers(){
  # writes header info into python files 
  # $1 end-year
  # $2 dir to look in
  # $3 excluded dir for find
  local YEAR_="${1:-}"
  local DIR_="${2:-}"



  echo "start finding files"
  mapfile -t PYTHON_FILES < <(find "${DIR_}" -type d -path "${PWD}/.*" -prune -false -o -type d -path "${PWD}/emba" -prune -false -o -iname "*.py")
  if [[ "${#PYTHON_FILES[@]}" -gt 0 ]]; then
    for FILE_ in "${PYTHON_FILES[@]}"; do


      local STARTYEAR="$(git log --follow --format=%ad --date default "${FILE_}" | tail -1 | cut -d ' ' -f 5)"
      local COPYRIGHT_HEADER="__copyright__ = 'Copyright ${STARTYEAR}-${YEAR} Siemens Energy AG'"
      local AUTHOR_ARR=()
      local AUTHOR_HEADER="__author__ = '"
      local LICENSE_HEADER="__license__ = 'MIT'" # Copyright 2021 The AMOS Projects TODO



      readarray -t AUTHOR_ARR < <(git shortlog -n -s "${FILE_}" 2>/dev/null | sort -gr | cut -c 8- ) # gets commit count for file/folder
      AUTHOR_ARR=( "${AUTHOR_ARR[@]/%/,}" )
      AUTHOR_HEADER+="${AUTHOR_ARR[@]}"
      AUTHOR_HEADER="${AUTHOR_HEADER%?}'"

      # debug messages
      echo "FILE: ${FILE_}"
      echo "get copyright: ${COPYRIGHT_HEADER}"
      echo "gets authors: ${AUTHOR_HEADER}"
      echo "file first line is:"
      head -n 1 "${FILE_}"
      echo


      # TODO write between imports and first
      
      if ! ( head -n 1 "${FILE_}" | grep -q '#' ) ; then
        echo "Doesn't have a #"

        sed -i "1s/^/${AUTHOR_HEADER}\n\n/" "${FILE_}"
        sed -i "1s/^/${COPYRIGHT_HEADER}\n/" "${FILE_}"
        sed -i "1s/^/${LICENSE_HEADER}\n/" "${FILE_}"
      else
        echo "HAS a #"

        EXCEPTIONS_TO_CHECK_ARR+=( "${FILE_}" )  
        echo -e "Found problem with ${ORANGE}${FILE_}""${NC}""\\n"
        echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"

      fi
    done
  else
    echo -e "\\n""${GREEN}""==> Found no Python files""${NC}""\\n"
  fi
}


write_headers 2024 "${PWD}/embark/embark/"


if [[ "${#EXCEPTIONS_TO_CHECK_ARR[@]}" -gt 0 ]]; then
  echo -e "${ORANGE}${BOLD}==> Please take a look at those Exceptions!""${NC}"
fi
echo -e "${GREEN}${BOLD}===> ALL CHECKS SUCCESSFUL""${NC}"
exit 0
