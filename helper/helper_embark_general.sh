#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020-2022 Siemens Energy AG
# Copyright 2020-2022 Siemens AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Helper functions

copy_file(){
  # check and copy file forcing overwrite
  # $1 : source
  # $2 : destination
  if ! [[ -f "$1" ]] ; then
    echo -e "\\n$RED""Could not find ""$1""$NC\\n"
  elif  ! [[ -d "$2" ]] || ! [[ -f "$2" ]] ; then
    echo -e "\\n$RED""Could not find ""$2""$NC\\n"
  fi
  cp -f "$1" "$2"
}

enable_strict_mode() {
  local STRICT_MODE_="$1"

  if [[ "$STRICT_MODE_" -eq 1 ]]; then
    # http://redsymbol.net/articles/unofficial-bash-strict-mode/
    # https://github.com/tests-always-included/wick/blob/master/doc/bash-strict-mode.md
    # shellcheck disable=SC1091
    source ./helper/wickStrictModeFail.sh
    set -e          # Exit immediately if a command exits with a non-zero status
    set -u          # Exit and trigger the ERR trap when accessing an unset variable
    set -o pipefail # The return value of a pipeline is the value of the last (rightmost) command to exit with a non-zero status
    set -E          # The ERR trap is inherited by shell functions, command substitutions and commands in subshells
    shopt -s extdebug # Enable extended debugging
    IFS=$'\n\t'     # Set the "internal field separator"
    trap 'wickStrictModeFail $? | tee -a /tmp/embark_error.log' ERR  # The ERR trap is triggered when a script catches an error

    if [[ "$PRINTER" -eq 1 ]]; then
      echo -e "[!] INFO: EMBArk STRICT mode enabled!"
    fi
  fi
}