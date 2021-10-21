#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

# Tidy returns
#0 = if everything is fine
#1 = if there were warnings and
#2 = if there were errors.

htmlcheck(){
  mapfile -t HTML_FILE < <(find embark -iname "*.html")
  for HTML_FILE in "${HTML_FILE[@]}"; do
    echo -e "\\n""$GREEN""Run tidy on $HTML_FILE:""$NC""\\n"
    #$( tidy "$HTML_FILE" -q 2>"$HTML_FILE.errors" 1>"$HTML_FILE.new" << EOF) 
    cat "$HTML_FILE" | tidy -q -f "$HTML_FILE.errors" -o "$HTML_FILE.new" >/dev/null 2>&1
    RES=$?
    if [[ $RES -eq 2 ]] ; then
      echo -e "\\n""$RED$BOLD==> FIX ERRORS""$NC""\\n"
      cat "$HTML_FILE.errors"
    elif [[ $RES -eq 1 ]]; then
      echo -e "\\n""$ORANGE$BOLD==> FIX WARNINGS""$NC""\\n"
      cat "$HTML_FILE.errors"
    elif [[ $RES -eq 0 ]]; then 
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
      mv "$HTML_FILE.new" "$HTML_FILE" # rename/replace
    else 
      echo -e "\\n""$RED$BOLD""[html-check(tidy)]ERRORS in SCRIPT""$NC""\\n"
    fi
  done
}
htmlcheck