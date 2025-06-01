#!/bin/bash

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="$1"
ZIPPATH="$2"
IS_UBUNTU=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
[[ ${IS_UBUNTU} == "Ubuntu" ]] && IS_UBUNTU=true || IS_UBUNTU=false

### Reset
rm -rf "${FILEPATH}"
rm -f "${ZIPPATH}"
mkdir -p "${FILEPATH}"

### Copy scripts
cp "emba_docker_installer.sh" "${FILEPATH}/installer.sh"

### Install needed tools
if ! which curl &> /dev/null; then
  apt-get update -y
  apt-get install -y curl
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

  apt install -y docker-ce
fi
systemctl is-active --quiet docker || systemctl start docker

### Find image
EMBAVERSION=$(curl -sL https://raw.githubusercontent.com/e-m-b-a/emba/refs/heads/master/docker-compose.yml \
  | awk -F: '/image:/ {print $NF; exit}')

### Export EMBA image
docker pull "embeddedanalyzer/emba:${EMBAVERSION}"
docker save -o "${FILEPATH}/emba-docker-image.tar" "embeddedanalyzer/emba:${EMBAVERSION}"
chmod 755 "${FILEPATH}/emba-docker-image.tar"
docker image rm "embeddedanalyzer/emba:${EMBAVERSION}"

tar czf "${ZIPPATH}" "${FILEPATH}"

