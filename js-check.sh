#!/bin/bash

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

jscheck(){
  mapfile -t JS_SCRIPTS < <(find embark -type d -name migrations -prune -false -o -iname "*.js")
  for JS_SCRIPT in "${JS_SCRIPTS[@]}"; do
    echo -e "\\n""$GREEN""Run jshint on $JS_SCRIPT:""$NC""\\n"
    # mapfile -t JS_RESULT < <(jshint "$JS_SCRIPT")
    jshint "$JS_SCRIPT" >> js-report  
  done
}

jscheck