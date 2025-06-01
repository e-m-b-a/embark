#!/bin/bash

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="$1"
ZIPPATH="$2"
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
rm -f "${ZIPPATH}"
mkdir -p "${FILEPATH}"

### Copy scripts
cp "deps_installer.sh" "${FILEPATH}/installer.sh"

### Install needed tools
if ! which curl &> /dev/null; then
  apt-get update -y
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

# Build index (for dependency tree)
( cd "${PKGPATH}" && dpkg-scanpackages . ) | gzip -9c > "${PKGPATH}/Packages.gz"

tar czf "${ZIPPATH}" "${FILEPATH}"
