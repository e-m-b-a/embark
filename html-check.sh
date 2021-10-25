#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color


# uses tidy to check for errors in all html files inside /embark (Django-root-dir)
# config in /embark/templates/uploader/.tidrc
htmlchecker(){
  mapfile -t HTML_FILE < <(find embark -iname "*.html")
  for HTML_FILE in "${HTML_FILE[@]}"; do
    echo -e "\\n""$GREEN""Run tidy on $HTML_FILE:""$NC""\\n"
    cat "$HTML_FILE" | tidy -q -f "$HTML_FILE.report" -o "$HTML_FILE.new" >/dev/null 2>&1 
    RES=$?
    if [[ $RES -eq 2 ]] ; then
      echo -e "\\n""$RED$BOLD==> FIX ERRORS""$NC""\\n"
      cat "$HTML_FILE.report"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$HTML_FILE" )
    elif [[ $RES -eq 1 ]]; then
      echo -e "\\n""$ORANGE$BOLD==> FIX WARNINGS""$NC""\\n"
      cat "$HTML_FILE.report"
      ((MODULES_TO_CHECK=MODULES_TO_CHECK+1))
      MODULES_TO_CHECK_ARR+=( "$HTML_FILE" )
    elif [[ $RES -eq 0 ]]; then 
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else 
      echo -e "\\n""$RED$BOLD""[html-check(tidy)]ERRORS in SCRIPT""$NC""\\n"
    fi
  done
}

htmlchecker