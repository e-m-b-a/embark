#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
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
INSTALLPATH="/root"
EXTERNALPATH="${INSTALLPATH}/emba/external"
EMBAMASTER="${INSTALLPATH}/emba-master"

rm -rf "${EMBAMASTER}"
mkdir "${EMBAMASTER}" && tar -xvzf "${FILEPATH}/emba.tar.gz" -C "${EMBAMASTER}" --strip-components 1

if [ -d "${EXTERNALPATH}" ]; then
  cp -r "${EXTERNALPATH}" "${EMBAMASTER}"
fi

rm -rf "${INSTALLPATH}/emba"

mv "${EMBAMASTER}" "${INSTALLPATH}/emba"
cp "${FILEPATH}/full_uninstaller.sh" "${INSTALLPATH}/emba"
cp "${FILEPATH}/git-head-meta" "${INSTALLPATH}/emba"
