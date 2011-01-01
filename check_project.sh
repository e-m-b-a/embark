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

# Description:  Check all shell and python scripts


GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

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
  if shellcheck ./check_project.sh || [[ $? -ne 1 && $? -ne 2 ]]; then
    echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
  else
    echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
    ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
    MODULES_TO_CHECK_ARR+=( "check_project.sh" )
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
  if command -v pycodstyle.py >/dev/null 2>&1; then
    echo -e "\\n""$ORANGE""pycodestyle found in PATH!""$NC""\\n"
    PYCODESTYLE="pycodestyle.py"
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
    if python3 "$PYCODESTYLE" --first "$PY_SCRIPT" || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$PY_SCRIPT" )
    fi
  done
}

pytester(){
  echo -e "[*] Test project with pytest (not supported)"
  #pytest
}

pylinter(){
  echo -e "\\n""$ORANGE""$BOLD""EMBArk pylint check""$NC""\\n""$BOLD""=================================================================""$NC"
  echo -e "[*] Do not forget to install the pylint-django plugin (e.g. apt-get install python3-pylint-django)" 
  mapfile -t PY_SCRIPTS < <(find embark -type d -name migrations -prune -false -o -iname "*.py")
  for PY_SCRIPT in "${PY_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run pylint on $PY_SCRIPT:""$NC""\\n"
    mapfile -t PY_RESULT < <(pylint --max-line-length=240 -d C0115,C0114,C0116,W0511 --load-plugins pylint_django "$PY_SCRIPT")
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
  pylint --max-line-length=240 -d C0115,C0114,C0116,W0511 --load-plugins pylint_django embark/* | grep "Your code has been rated"
  # current rating: 9.52/10
  # start rating: 5.58/10
}

MODULES_TO_CHECK=0
MODULES_TO_CHECK_ARR=()
shellchecker
pycodestyle_check
pylinter
# pytester


if [[ "${#MODULES_TO_CHECK_ARR[@]}" -gt 0 ]]; then
  echo -e "\\n\\n""$GREEN$BOLD""SUMMARY:$NC\\n"
  echo -e "Modules to check: $MODULES_TO_CHECK\\n"
  for MODULE in "${MODULES_TO_CHECK_ARR[@]}"; do
    echo -e "$ORANGE$BOLD==> FIX MODULE: ""$MODULE""$NC"
  done
fi
