#!/bin/bash

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="$1"
ZIPPATH="$2"
EXTERNALPATH="${FILEPATH}/external"

### Reset
rm -rf "${FILEPATH}"
rm -f "${ZIPPATH}"
mkdir -p "${FILEPATH}"

### Copy scripts
cp "external_installer.sh" "${FILEPATH}/installer.sh"

### Download external data
mkdir -p "${EXTERNALPATH}"
if [ ! -d "${EXTERNALPATH}/nvd-json-data-feeds" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/nvd-json-data-feeds.git "${EXTERNALPATH}/nvd-json-data-feeds"
fi
if [ ! -d "${EXTERNALPATH}/EPSS-data" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/EPSS-data.git "${EXTERNALPATH}/EPSS-data"
fi

### Fake venv (packages are broken)
mkdir -p "${EXTERNALPATH}/emba_venv/bin"
touch "${EXTERNALPATH}/emba_venv/bin/activate"

tar czf "${ZIPPATH}" -C "${FILEPATH}" .
