YEAR=2024










write_headers(){
  # writes header info into python files 
  # $1 end-year
  # $2 dir to look in
  # $3 excluded dir for find
  local YEAR_="${1:-}"
  local DIR_="${2:-}"




  echo "start finding files"
  mapfile -t PYTHON_FILES < <(find "${DIR_}" -type d -path "${PWD}/emba" -prune -false -o -iname "*.py")
  if [[ "${#PYTHON_FILES[@]}" -gt 0 ]]; then
    for FILE_ in "${PYTHON_FILES[@]}"; do


      local STARTYEAR= # TODO
      local COPYRIGHT="__copyright__ = 'Copyright ${STARTYEAR} - ${YEAR}'"
        local AUTHOR_ARR="$(git shortlog -n -s -- "${FILE_}")" # gets commit count for file/folder
      local AUTHOR="__author__ = '${AUTHOR_ARR}'" #TODO

      if ! grep -q "${YEAR_}.*Siemens Energy AG" "${LINE_%%:*}" && ! grep -q "Siemens AG" "${LINE_%%:*}"; then
        ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
        MODULES_TO_CHECK_ARR+=( "${LINE_%%:*}" )  
        echo -e "Found problem with Copyright in ${LINE_%%:*}: ${ORANGE}${LINE_##*:}""${NC}""\\n"
        echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      fi
    done
  else
    echo -e "\\n""${GREEN}""==> Found no problems with copyrights""${NC}""\\n"
  fi
}


write_headers 2024 "${PWD}" 