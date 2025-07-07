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

FILEPATH="$1"
ZIPPATH="$2"
VERSION="$3"
EXTERNALPATH="${FILEPATH}/external"

NVD_VERSION=$(echo "${VERSION}" | cut -d \, -f 1)
EPSS_VERSION=$(echo "${VERSION}" | cut -d \, -f 2)

### Reset
rm -rf "${FILEPATH}"
rm -f "${ZIPPATH}"
mkdir -p "${FILEPATH}"

### Copy scripts
cp "external_installer.sh" "${FILEPATH}/installer.sh"

### Download external data
mkdir -p "${EXTERNALPATH}"

git clone https://github.com/EMBA-support-repos/nvd-json-data-feeds.git "${EXTERNALPATH}/nvd-json-data-feeds"
if [ "${NVD_VERSION}" = "latest" ]; then
	git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout main
else
	git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout "${NVD_VERSION}"
fi
git -C "${EXTERNALPATH}/nvd-json-data-feeds" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/nvd-json-data-feeds/git-head-meta"
rm -rf "${EXTERNALPATH}/nvd-json-data-feeds/.git"

git clone https://github.com/EMBA-support-repos/EPSS-data.git "${EXTERNALPATH}/EPSS-data"
if [ "${EPSS_VERSION}" = "latest" ]; then
	git -C "${EXTERNALPATH}/EPSS-data" checkout main
else
	git -C "${EXTERNALPATH}/EPSS-data" checkout "${EPSS_VERSION}"
fi
git -C "${EXTERNALPATH}/EPSS-data" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/EPSS-data/git-head-meta"
rm -rf "${EXTERNALPATH}/EPSS-data/.git"

### Fake venv (packages are broken)
mkdir -p "${EXTERNALPATH}/emba_venv/bin"
touch "${EXTERNALPATH}/emba_venv/bin/activate"

tar czf "${ZIPPATH}" -C "${FILEPATH}" .
