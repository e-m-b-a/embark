#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): ClProsser, SirGankalot

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="."
EXTERNALPATH="${FILEPATH}/external"
EMBAPATH="/root/emba"

[ -d "${EMBAPATH}" ] || exit 1

rm -rf "${EMBAPATH}/external"
cp -r "${EXTERNALPATH}" "${EMBAPATH}"
