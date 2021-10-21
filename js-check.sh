#!/bin/bash

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

# checks js-scripts with jshint for errors
# config @ ./embark/static/.jshintrc
jscheck(){
  mapfile -t JS_SCRIPTS < <(find embark -iname "*.js")
  for JS_SCRIPT in "${JS_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run jshint on $JS_SCRIPT:""$NC""\\n"
    # mapfile -t JS_RESULT < <(jshint "$JS_SCRIPT")
    jshint "$JS_SCRIPT" >"$JS_SCRIPT.report"
    RES=$?
    echo -e "$RES"
    if [[ $RES -eq 2 ]] ; then
      echo -e "\\n""$RED$BOLD==> FIX ERRORS""$NC""\\n"
      cat "$JS_SCRIPT.report"
    elif [[ $RES -eq 1 ]]; then
      echo -e "\\n""$ORANGE$BOLD==> FIX WARNINGS""$NC""\\n"
      cat "$JS_SCRIPT.report"
    elif [[ $RES -eq 0 ]]; then 
      echo -e "$GREEN""$BOLD""==> SUCCESS""$NC""\\n"
    else 
      echo -e "\\n""$RED$BOLD""[jshint]ERRORS in SCRIPT""$NC""\\n"
    fi
  done
}

jscheck