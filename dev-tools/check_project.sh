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
# Contributer(s): Benedikt Kuehne

# Description:  Check all scripts and templates(Django gets its own unit-tests)
#               And check Django if its deployable

export DJANGO_SETTINGS_MODULE=embark.settings
export PYTHONPATH="$PYTHONPATH:${PWD}/embark/embark/"

cd "$(dirname "$0")" || exit 1
cd .. || exit 1 

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

if [[ $EUID -eq 0 ]]; then
  echo -e "\\n$RED""Running this script as root is not supported""$NC\\n"
fi

# check that all tools are installed
check_tools(){
  TOOLS=("jshint" "shellcheck" "pylint")
  for TOOL in "${TOOLS[@]}";do
    if ! command -v "$TOOL" > /dev/null ; then 
      echo -e "\\n""$RED""$TOOL is not installed correctly""$NC""\\n"
      exit 1
    fi
  done
  pipenv run djlint --version | grep "version"; RES=$?
  if [[ -z "$RES" ]];then
    echo -e "\\n""$RED""djlint(pip) is not installed correctly""$NC""\\n"
  fi
}

# checks django configuration
check_django(){
  cd ./embark || exit 1
  pipenv run python ./embark/manage.py check --deploy
  cd .. || exit 1
}

# checks js-scripts with jshint for errors
# config @ ./embark/static/.jshintrc
jscheck(){
  mapfile -t JS_SCRIPTS < <(find ./embark -iname "*.js")
  for JS_SCRIPT in "${JS_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run jshint on $JS_SCRIPT:""$NC""\\n"
    # mapfile -t JS_RESULT < <(jshint "$JS_SCRIPT")
    jshint "$JS_SCRIPT" >/dev/null
    RES=$?
    if [[ $RES -eq 2 ]] ; then
      echo -e "\\n""$RED$BOLD==> FIX ERRORS""$NC""\\n"
      cat "$JS_SCRIPT.report"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$JS_SCRIPT" )
    elif [[ $RES -eq 1 ]]; then
      echo -e "\\n""$ORANGE$BOLD==> FIX WARNINGS""$NC""\\n"
      cat "$JS_SCRIPT.report"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$JS_SCRIPT" )
    elif [[ $RES -eq 0 ]]; then 
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else 
      echo -e "\\n""$RED$BOLD""[jshint]ERRORS in SCRIPT""$NC""\\n"
    fi
    # TODO: ADD the Module_check thingy
  done
}

# uses djlint to check for errors in all html-template files inside /embark (Django-root-dir)
# no config
templatechecker(){
  mapfile -t HTML_FILE < <(find ./embark -iname "*.html")
  for HTML_FILE in "${HTML_FILE[@]}"; do
    echo -e "\\n""$GREEN""Run djlint on $HTML_FILE:""$NC""\\n"
    pipenv run djlint "$HTML_FILE"
    RES=$?
    if [[ $RES -eq 1 ]]; then
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$HTML_FILE" )
    elif [[ $RES -eq 0 ]]; then 
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else 
      echo -e "\\n""$RED$BOLD""[html-check(tidy)]ERRORS in SCRIPT""$NC""\\n"
    fi
  done
}

shellchecker() {
  echo -e "\\n""$ORANGE""$BOLD""EMBArk Shellcheck""$NC""\\n""$BOLD""=================================================================""$NC"
  if ! command -v shellcheck >/dev/null 2>&1; then
    echo -e "\\n""$ORANGE""Shellcheck not found!""$NC""\\n""$ORANGE""Install shellcheck via 'apt-get install shellcheck'!""$NC\\n"
    exit 1
  fi

  echo -e "\\n""$GREEN""Run shellcheck on installer:""$NC""\\n"
  if shellcheck ./installer.sh || [[ $? -ne 1 && $? -ne 2 ]]; then
    echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
  else
    echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
    ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
    MODULES_TO_CHECK_ARR+=( "installer.sh" )
  fi

  echo -e "\\n""$GREEN""Run shellcheck on this script:""$NC""\\n"
  if shellcheck ./dev-tools/check_project.sh || [[ $? -ne 1 && $? -ne 2 ]]; then
    echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
  else
    echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
    ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
    MODULES_TO_CHECK_ARR+=( "dev-tools/check_project.sh" )
  fi

  echo -e "\\n""$GREEN""Find shell scripts and run shellcheck on them:""$NC""\\n"
  mapfile -t SH_SCRIPTS < <(find embark -iname "*.sh")
  for SH_SCRIPT in "${SH_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run shellcheck on $SH_SCRIPT:""$NC""\\n"
    if shellcheck "$SH_SCRIPT" || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$SH_SCRIPT" )
    fi
  done
}

pycodestyle_check(){
  echo -e "\\n""$ORANGE""$BOLD""EMBArk pycodestyle check""$NC""\\n""$BOLD""=================================================================""$NC"
  echo -e "[*] Searching python files and test with pycodestyle.py"
  if command -v pipenv run pycodstyle >/dev/null 2>&1; then
    echo -e "\\n""$ORANGE""pycodestyle found in PATH!""$NC""\\n"
    PYCODESTYLE="pycodestyle"
  elif [[ -f "/usr/lib/python3/dist-packages/pycodestyle.py" ]]; then
    echo -e "\\n""$ORANGE""pycodestyle found!""$NC""\\n"
    PYCODESTYLE="/usr/lib/python3/dist-packages/pycodestyle.py"
  else
    echo -e "\\n""$ORANGE""pycodestyle not found!""$NC""\\n""$ORANGE""Install pycodestyle via 'apt-get install pycodestyle'!""$NC\\n"
    exit 1
  fi

  echo -e "\\n""$GREEN""Find python scripts and run pycodestyle on them:""$NC""\\n"
  mapfile -t PY_SCRIPTS < <(find embark -iname "*.py")
  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run pycodestyle on $PY_SCRIPT:""$NC""\\n"
    if pipenv run "$PYCODESTYLE" --first "$PY_SCRIPT" || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$PY_SCRIPT" )
    fi
  done
}

banditer() {
  echo -e "\\n""$ORANGE""$BOLD""EMBArk bandit check""$NC""\\n""$BOLD""=================================================================""$NC"
  if command -v bandit >/dev/null 2>&1; then
    echo -e "\\n""$ORANGE""bandit found in PATH!""$NC""\\n"
  else
    echo -e "\\n""$ORANGE""bandit not found!""$NC""\\n""$ORANGE""Install bandit via 'apt-get install bandit'!""$NC\\n"
    exit 1
  fi

  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run bandit on $PY_SCRIPT:""$NC""\\n"
    if bandit -c .banditrc "$PY_SCRIPT" 2> /dev/null | grep -q "No issues identified."; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      bandit -c .banditrc "$PY_SCRIPT"
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$PY_SCRIPT" )
    fi
  done

}

pylinter(){
  cd ./embark || exit 1
  echo -e "\\n""$ORANGE""$BOLD""EMBArk pylint check""$NC""\\n""$BOLD""=================================================================""$NC"
  mapfile -t PY_SCRIPTS < <(find . -type d -name migrations -prune -false -o -iname "*.py")
  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run pylint on $PY_SCRIPT:""$NC""\\n"
    mapfile -t PY_RESULT < <(pipenv run pylint --rcfile=../.pylintrc "$PY_SCRIPT")
    local RATING_10=0
    if [[ "${#PY_RESULT[@]}" -gt 0 ]]; then 
      if ! printf '%s\n' "${PY_RESULT[@]}" | grep -q -P '^Your code has been rated at 10'; then
        for LINE in "${PY_RESULT[@]}"; do
          echo "$LINE"
        done
      else
        RATING_10=1
      fi
      if [[ "$RATING_10" -ne 1 ]]; then
        echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
        ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
        MODULES_TO_CHECK_ARR+=( "$PY_SCRIPT" )
      else
        echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
      fi
    else
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    fi
  done

  echo -e "\\n""$GREEN""Run pylint on all scripts:""$NC""\\n"
  pipenv run pylint --rcfile=../.pylintrc ./* | grep "Your code has been rated"
  # current rating: 9.52/10
  # start rating: 5.58/10
  cd .. || exit 1
}

dockerchecker(){
  echo -e "\\n""$ORANGE""$BOLD""EMBArk docker-files check""$NC""\\n""$BOLD""=================================================================""$NC"
  mapfile -t DOCKER_COMPS < <(find .  -maxdepth 1 -type d -name migrations -prune -false -o -iname "docker-compose*.yml")
  for DOCKER_COMP in "${DOCKER_COMPS[@]}"; do
    if ! docker-compose -f "$DOCKER_COMP" config 1>/dev/null; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$DOCKER_COMP" )    
    fi
  done
  #TODO dockerfile itself
}

#main
check_tools
MODULES_TO_CHECK=0
MODULES_TO_CHECK_ARR=()
shellchecker
dockerchecker
jscheck
templatechecker
pycodestyle_check
banditer
pylinter
#check_django TODO

if [[ "${#MODULES_TO_CHECK_ARR[@]}" -gt 0 ]]; then
  echo -e "\\n\\n""$GREEN$BOLD""SUMMARY:$NC\\n"
  echo -e "Modules to check: $MODULES_TO_CHECK\\n"
  for MODULE in "${MODULES_TO_CHECK_ARR[@]}"; do
    echo -e "$ORANGE$BOLD==> FIX MODULE: ""$MODULE""$NC"
  done
  exit 1
fi
exit 0