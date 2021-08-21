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
  fi

  echo -e "\\n""$GREEN""Run shellcheck on this script:""$NC""\\n"
  if shellcheck ./codestyle_check.sh || [[ $? -ne 1 && $? -ne 2 ]]; then
    echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
  else
    echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
  fi

  echo -e "\\n""$GREEN""Find shell scripts and run shellcheck on them:""$NC""\\n"
  mapfile -t SH_SCRIPTS < <(find embark -iname "*.sh")
  for SH_SCRIPT in "${SH_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run shellcheck on $SH_SCRIPT:""$NC""\\n"
    if shellcheck "$SH_SCRIPT" || [[ $? -ne 1 && $? -ne 2 ]]; then
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else
      echo -e "\\n""$ORANGE$BOLD==> FIX ERRORS""$NC""\\n"
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
    fi
  done
}

pytester(){
  echo -e "[*] Test project with pytest (not supported)"
  #pytest
}

pylinter(){
  echo -e "[*] Searching python files and test with pylint (under construction)"
  pylint --max-line-length=240 embark/*
  # current rating: 5.58/10
}

shellchecker
pycodestyle_check
pytester
pylinter



