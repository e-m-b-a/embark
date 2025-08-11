#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
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

### Reset
rm -rf "${FILEPATH}"
rm -f "${ZIPPATH}"
mkdir -p "${FILEPATH}"

### Copy scripts
cp "emba_repo_installer.sh" "${FILEPATH}/installer.sh"
cp "full_uninstaller.sh" "${FILEPATH}"

### Install needed tools
if ! which curl &> /dev/null; then
  apt-get update -y
  apt-get install -y curl
fi

### Download EMBA
if [ "${VERSION}" = "latest" ]; then
  curl -L --url https://github.com/e-m-b-a/emba/archive/refs/heads/master.tar.gz --output "${FILEPATH}/emba.tar.gz"
  sha=$(git ls-remote https://github.com/e-m-b-a/emba HEAD | awk '{print $1}')
  echo "${sha} N/A" > "${FILEPATH}/git-head-meta"
else
  curl -L --url "https://github.com/e-m-b-a/emba/archive/${VERSION}.tar.gz" --output "${FILEPATH}/emba.tar.gz"
  echo "${VERSION} N/A" > "${FILEPATH}/git-head-meta"
fi

tar czf "${ZIPPATH}" -C "${FILEPATH}" .
