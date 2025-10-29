#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2025 Siemens Energy AG
# Copyright 2020-2021 Siemens AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Michael Messner, Pascal Eckmann
# Contributor(s): Benedikt Kuehne, ClProsser

# Description:  Check all scripts and templates(Django gets its own unit-tests)
#               And check Django if its deployable

export DJANGO_SETTINGS_MODULE=embark.settings.dev
export PYTHONPATH="${PYTHONPATH}:${PWD}/embark/embark/:${PWD}/embark/"
export PIPENV_VENV_IN_PROJECT="True"

cd "$(dirname "${0}")" || exit 1
cd .. || exit 1

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

if [[ ${EUID} -eq 0 ]]; then
  echo -e "\\n${RED}""Running this script as root is not supported""${NC}\\n"
fi

if [[ "$*" == *"--fast"* ]]; then
  FAST_EXECUTION=1
elif [[ "$*" == *"--help"* ]]; then
  echo "Usage: ${0} [--fast]"
  exit 0
fi

# check that all tools are installed
check_tools(){
  TOOLS=("jshint" "shellcheck" "pylint" "yamllint")
  for TOOL in "${TOOLS[@]}";do
    if ! command -v "${TOOL}" > /dev/null ; then
      echo -e "\\n""${RED}""${TOOL} is not installed correctly""${NC}""\\n"
      exit 1
    fi
  done
  pipenv run djlint --version | grep "version"; RES=$?
  if [[ -z "${RES}" ]];then
    echo -e "\\n""${RED}""djlint(pip) is not installed correctly""${NC}""\\n"
  fi
}

# checks django configuration
check_django(){
  cd ./embark || exit 1
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk django-settings check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if ! pipenv run python ./manage.py check | grep -q "System check identified no issues"; then  #TODO add --deploy flag
      echo -e "\\n""${RED}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "./embark/settings/" )
  else
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
  fi
  cd .. || exit 1
}

# checks js-scripts with jshint for errors
# config @ .jshintrc
jscheck(){
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk javascript-files check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
     mapfile -t JS_SCRIPTS < <(git status -s | grep ".*.js$" | awk '{print $2}' | sort -u)
  else
    mapfile -t JS_SCRIPTS < <(find ./embark -iname "*.js")
  fi
  for JS_SCRIPT in "${JS_SCRIPTS[@]}"; do
    echo -e "\\n""${GREEN}""Run jshint on ${JS_SCRIPT}:""${NC}""\\n"
    # mapfile -t JS_RESULT < <(jshint "${JS_SCRIPT}")
    jshint -c ./.jshintrc "${JS_SCRIPT}"
    RES=$?
    if [[ ${RES} -eq 2 ]] ; then
      echo -e "\\n""${RED}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${JS_SCRIPT}" )
    elif [[ ${RES} -eq 1 ]]; then
      echo -e "\\n""${ORANGE}${BOLD}==> FIX WARNINGS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${JS_SCRIPT}" )
    elif [[ ${RES} -eq 0 ]]; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${RED}${BOLD}""[jshint]ERRORS in SCRIPT""${NC}""\\n"
    fi
  done
}

# uses djlint to check for errors in all html-template files inside /embark (Django-root-dir)
# no config
templatechecker(){
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk html-templates check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
     mapfile -t HTML_FILES < <(git status -s | grep ".*.html$" | awk '{print $2}' | sort -u)
  else
    mapfile -t HTML_FILES < <(find ./embark -iname "*.html")
  fi
  for HTML_FILE in "${HTML_FILES[@]}"; do
    echo -e "\\n""${GREEN}""Run djlint on ${HTML_FILE}:""${NC}""\\n"
    pipenv run djlint "${HTML_FILE}"
    RES=$?
    if [[ ${RES} -eq 1 ]]; then
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${HTML_FILE}" )
    elif [[ ${RES} -eq 0 ]]; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${RED}${BOLD}""[html-check(tidy)]ERRORS in SCRIPT""${NC}""\\n"
    fi
  done
}

shellchecker() {
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk Shellcheck""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  echo -e "\\n""${GREEN}""Find shell scripts and run shellcheck on them:""${NC}""\\n"
   if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
     mapfile -t SH_SCRIPTS < <(git status -s | grep ".*.sh$" | awk '{print $2}' | sort -u)
  else
    mapfile -t SH_SCRIPTS < <(find . -not -path "./emba/*" -not -path "./.*" -not -path "./embark_db/*" -iname "*.sh" 2> /dev/null)
  fi
  for SH_SCRIPT in "${SH_SCRIPTS[@]}"; do
    echo -e "\\n""${GREEN}""Run shellcheck on ${SH_SCRIPT}:""${NC}""\\n"
    if shellcheck -x -o require-variable-braces "${SH_SCRIPT}" || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${SH_SCRIPT}" )
    fi
  done
}

pycodestyle_check(){
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk pycodestyle check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  echo -e "[*] Searching python files and test with pycodestyle.py"
  if command -v pipenv run pycodstyle >/dev/null 2>&1; then
    echo -e "\\n""${ORANGE}""pycodestyle found in PATH!""${NC}""\\n"
    PYCODESTYLE="pycodestyle"
  elif [[ -f "/usr/lib/python3/dist-packages/pycodestyle.py" ]]; then
    echo -e "\\n""${ORANGE}""pycodestyle found!""${NC}""\\n"
    PYCODESTYLE="/usr/lib/python3/dist-packages/pycodestyle.py"
  else
    echo -e "\\n""${ORANGE}""pycodestyle not found!""${NC}""\\n""${ORANGE}""Install pycodestyle via 'apt-get install pycodestyle'!""${NC}\\n"
    exit 1
  fi

  echo -e "\\n""${GREEN}""Find python scripts and run pycodestyle on them:""${NC}""\\n"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
    mapfile -t PY_SCRIPTS < <(git status -s | grep ".*.py$" | awk '{print $2}' | sort -u)
  else
    mapfile -t PY_SCRIPTS < <(find ./embark -type d -name migrations -prune -false -o -iname "*.py$")
  fi
  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""${GREEN}""Run pycodestyle on ${PY_SCRIPT}:""${NC}""\\n"
    if pipenv run "${PYCODESTYLE}" --config=./.pycodestylerc --first "${PY_SCRIPT}" 2> >(grep -v "Courtesy Notice\|Loading .env" >&2) || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${PY_SCRIPT}" )
    fi
  done
}

banditer() {
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk bandit check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if command -v bandit >/dev/null 2>&1; then
    echo -e "\\n""${ORANGE}""bandit found in PATH!""${NC}""\\n"
  else
    echo -e "\\n""${ORANGE}""bandit not found!""${NC}""\\n""${ORANGE}""Install bandit via 'apt-get install bandit'!""${NC}\\n"
    exit 1
  fi

  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
    mapfile -t PY_SCRIPTS < <(git status -s | grep ".*.py$" | awk '{print $2}' | sort -u)
  else
    mapfile -t PY_SCRIPTS < <(find ./embark -type d -name migrations -prune -false -o -iname "*.py$")
  fi

  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""${GREEN}""Run bandit on ${PY_SCRIPT}:""${NC}""\\n"
    if bandit -c .banditrc "${PY_SCRIPT}" 2> /dev/null | grep -q "No issues identified."; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      bandit -c .banditrc "${PY_SCRIPT}"
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${PY_SCRIPT}" )
    fi
  done

}

pylinter(){
  cd ./embark || exit 1
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk pylint check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
    mapfile -t PY_SCRIPTS < <(git status -s | grep ".*.py$" | awk '{print $2}' | sort -u)
  else
    mapfile -t PY_SCRIPTS < <(find ./embark -type d -name migrations -prune -false -o -iname "*.py$")
  fi
  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""${GREEN}""Run pylint on ${PY_SCRIPT}:""${NC}""\\n"
    mapfile -t PY_RESULT < <(pipenv run pylint --load-plugins pylint_django --rcfile=../.pylintrc "${PY_SCRIPT}" 2> >(grep -v "Courtesy Notice\|Loading .env" >&2) )
    local RATING_10=0
    if [[ "${#PY_RESULT[@]}" -gt 0 ]]; then
      if ! printf '%s\n' "${PY_RESULT[@]}" | grep -q -P '^Your code has been rated at 10'; then
        for LINE in "${PY_RESULT[@]}"; do
          echo "${LINE}"
        done
      else
        RATING_10=1
      fi
      if [[ "${RATING_10}" -ne 1 ]]; then
        echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
        ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
        MODULES_TO_CHECK_ARR+=( "${PY_SCRIPT}" )
      else
        echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
      fi
    else
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    fi
  done

  cd .. || exit 1
}

dockerchecker(){
  if ! [[ -f .env ]]; then
    ENV=1
    touch .env  # dummy file
  else
    ENV=0
  fi
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk docker-files check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
    mapfile -t DOCKER_COMPS < <(git status -s | grep ".*docker-compose.*.yml$" | awk '{print $2}' | sort -u)
  else
    mapfile -t DOCKER_COMPS < <(find . -maxdepth 1 -type d -name migrations -prune -false -o -iname "docker-compose*.yml")
  fi

  for DOCKER_COMP in "${DOCKER_COMPS[@]}"; do
    echo -e "\\n""${GREEN}""Run docker check on ${DOCKER_COMP}:""${NC}""\\n"
    if docker compose -f "${DOCKER_COMP}" config 1>/dev/null || [[ $? -ne 1 ]]; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${DOCKER_COMP}" )
    fi
  done
  #TODO dockerlinter -f ./Dockerfile
  if [[ ${ENV} -gt 0 ]]; then
    rm .env   #remove dummy
  fi
}

yamlchecker(){
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk yaml-files check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if [[ "${FAST_EXECUTION:-0}" -eq 1 ]]; then
    mapfile -t YAML_COMPS < <(git status -s | grep ".*.yml$" | awk '{print $2}' | sort -u)
  else
    mapfile -t YAML_COMPS < <(find . -maxdepth 1 -type d -name migrations -prune -false -o -iname "*.yml")
  fi
  for YAML_COMP_ in "${YAML_COMPS[@]}"; do
    echo -e "\\n""${GREEN}""Run docker check on ${YAML_COMP_}:""${NC}""\\n"
    if yamllint "${YAML_COMP_}" ; then
      echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
    else
      echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "${YAML_COMP_}" )
    fi
  done
}

openapichecker(){
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk openapi spec check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  if spectral lint ./docs/openapi.yaml ; then
    echo -e "${GREEN}""${BOLD}""==> SUCCESS""${NC}""\\n"
  else
    echo -e "\\n""${ORANGE}${BOLD}==> FIX ERRORS""${NC}""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "./docs/openapi.yaml" )
  fi
}

list_linter_exceptions(){
  # lists all linter exceptions for a given toolname inside a directory
  # $1 tool name
  # $2 directory
  # $3 excluded dir for find

  if $FAST_EXECUTION; then return 0; fi

  local TOOL_NAME_="${1:-}"
  local DIR_="${2:-}"
  local EXCLUDE_="${3:-}"
  local SEARCH_PAR_=""
  local SEARCH_TYPE_=""
  echo -e "\\n""${GREEN}""Checking for ${TOOL_NAME_} exceptions inside ${DIR_}:""${NC}""\\n"
  case "${TOOL_NAME_}" in
    jshint)
      SEARCH_PAR_="jshint ignore"
      SEARCH_TYPE_="js"
      ;;
    shellcheck)
      SEARCH_PAR_="shellcheck disable"
      SEARCH_TYPE_="sh"
      ;;
    bandit)
      SEARCH_PAR_=" nosec"
      SEARCH_TYPE_="py"
      ;;
    pylint)
      SEARCH_PAR_="pylint: disable"
      SEARCH_TYPE_="py"
      ;;
    djlint)
      SEARCH_PAR_="djlint"
      SEARCH_TYPE_="html"
      ;;
  esac
  mapfile -t EXCEPTION_SCRIPTS < <(find "${DIR_}" -type d -path "${EXCLUDE_}" -prune -false -o -iname "*.${SEARCH_TYPE_}" -exec grep -H "${SEARCH_PAR_}" {} \;)
  if [[ "${#EXCEPTION_SCRIPTS[@]}" -gt 0 ]]; then
    for EXCEPTION_ in "${EXCEPTION_SCRIPTS[@]}"; do
      echo -e "\\n""${GREEN}""Found exception in ${EXCEPTION_%%:*}:""${ORANGE}""${EXCEPTION_##*:}""${NC}""\\n"
      EXCEPTIONS_TO_CHECK_ARR+=( "${EXCEPTION_%%:*}" )
    done
  else
    echo -e "\\n""${GREEN}""=> Found no exceptions for ${TOOL_NAME_}""${NC}""\\n"
  fi
}

copy_right_check(){
  # checks all Copyright occurrences for supplied end-year
  # $1 end-year
  # $2 dir to look in
  # $3 excluded dir for find
  local YEAR_="${1:-}"
  local DIR_="${2:-}"
  local EXCLUDE_="${3:-}"
  echo -e "\\n""${ORANGE}""${BOLD}""EMBArk Copyright check""${NC}""\\n""${BOLD}""=================================================================""${NC}"
  mapfile -t COPYRIGHT_LINE_ < <(find "${DIR_}" -type d -path "${PWD}/emba" -prune -false -o -type d -path "${EXCLUDE_}" -prune -false -o -type f -path "${0}" -prune -false -o -iname "*.sh" -exec grep -H "Copyright" {} \;)
  if [[ "${#COPYRIGHT_LINE_[@]}" -gt 0 ]]; then
    for LINE_ in "${COPYRIGHT_LINE_[@]}"; do
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

#main
check_tools
MODULES_TO_CHECK=0
MODULES_TO_CHECK_ARR=()
EXCEPTIONS_TO_CHECK_ARR=()
shellchecker
list_linter_exceptions "shellcheck" "$PWD"
dockerchecker
jscheck
list_linter_exceptions "jshint" "$PWD/embark"
templatechecker
list_linter_exceptions "djlint" "$PWD/embark"
pycodestyle_check
banditer
list_linter_exceptions "bandit" "$PWD/embark"
pylinter
list_linter_exceptions "pylint" "$PWD/embark"
check_django
yamlchecker
openapichecker

if [[ "$(date +%Y)" -ne 2025 ]]; then
  copy_right_check 2025 "${PWD}" "${PWD}/emba_logs"
fi

if [[ "${#MODULES_TO_CHECK_ARR[@]}" -gt 0 ]]; then
  echo -e "\\n\\n""${GREEN}${BOLD}""SUMMARY:${NC}\\n"
  echo -e "Modules to check: ${MODULES_TO_CHECK}\\n"
  for MODULE in "${MODULES_TO_CHECK_ARR[@]}"; do
    echo -e "${RED}${BOLD}==> FIX MODULE: ""${MODULE}""${NC}"
  done
  exit 1
fi
if [[ "${#EXCEPTIONS_TO_CHECK_ARR[@]}" -gt 0 ]]; then
  echo -e "${ORANGE}${BOLD}==> Please take a look at those Exceptions!""${NC}"
fi

echo -e "${GREEN}${BOLD}===> ALL CHECKS SUCCESSFUL""${NC}"
exit 0
