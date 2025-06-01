#!/bin/bash

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
