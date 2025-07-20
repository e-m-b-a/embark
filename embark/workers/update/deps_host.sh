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
# Contributor(s): Luka Dekanozishvili

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="$1"
ZIPPATH="$2"
VERSION="$3"
DEPSCACHE="$4"

PKGPATH="${FILEPATH}/pkg"
IS_UBUNTU=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
[[ ${IS_UBUNTU} == "Ubuntu" ]] && IS_UBUNTU=true || IS_UBUNTU=false

function downloadPackage() {
  # shellcheck disable=SC2046
  ( cd "${PKGPATH}" && apt-get download $(apt-cache depends --recurse --no-recommends --no-suggests \
    --no-conflicts --no-breaks --no-replaces --no-enhances \
    --no-pre-depends "$@" | grep "^\w") )
}

### Reset
rm -rf "${FILEPATH}"

if [ -n "${ZIPPATH}" ]; then
  rm -f "${ZIPPATH}"
fi

mkdir -p "${FILEPATH}"

### Copy scripts
cp "deps_installer.sh" "${FILEPATH}/installer.sh"

apt-get update -y

if [ "${VERSION}" = "latest" ] || [ ! -d "${DEPSCACHE}/pkg" ]; then
  ### Add some required sources if they haven't been added yet
  if [ ! -f /etc/apt/sources.list.d/embark.list ]; then
    echo 'deb http://archive.ubuntu.com/ubuntu jammy main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://security.ubuntu.com/ubuntu jammy-security main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://archive.ubuntu.com/ubuntu jammy-updates main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://archive.ubuntu.com/ubuntu focal main universe' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    apt-get update -y
  fi

  ### Install needed tools
  if ! which curl &> /dev/null; then
    apt-get install -y curl
  fi

  if ! which dpkg-scanpackages &> /dev/null; then
    apt-get install -y dpkg-dev
  fi

  if ! which docker &> /dev/null; then
    apt-get install -y ca-certificates
    install -m 0755 -d /etc/apt/keyrings

    if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
      if [ "${IS_UBUNTU}" = true ] ; then
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
	# shellcheck source=/dev/null
	echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
	  $(. /etc/os-release && echo "${UBUNTU_CODENAME}:-${VERSION_CODENAME}") stable" | \
	  tee /etc/apt/sources.list.d/docker.list > /dev/null
      else
	curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
	echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | \
	  tee /etc/apt/sources.list.d/docker.list > /dev/null
      fi

      chmod a+r /etc/apt/keyrings/docker.asc
      apt-get update -y
    fi

    apt-get install -y docker-ce
  fi
  systemctl is-active --quiet docker || systemctl start docker

  ### Download debs from https://packages.debian.org/sid/amd64/<packagename>/download
  mkdir -p "${PKGPATH}"

  # Needed to run EMBA:
  downloadPackage docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Needed for EMBA:
  downloadPackage inotify-tools
  downloadPackage libnotify-bin
  downloadPackage p7zip-full

  # Build index (for dependency tree)
  ( cd "${PKGPATH}" && dpkg-scanpackages . ) | gzip -9c > "${PKGPATH}/Packages.gz"
else
  cp -rf "${DEPSCACHE}/pkg" "${PKGPATH}"
fi

if [ -n "${ZIPPATH}" ]; then
  tar czf "${ZIPPATH}" -C "${FILEPATH}" .
fi
