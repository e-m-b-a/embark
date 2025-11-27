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
# Contributor(s): Benedikt Kuehne

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting EMBA Docker image preparation script"
echo -e "[*] Output Directory: $1"
echo -e "[*] ZIP Output Path: $2"
echo -e "[*] Version: $3\n"

FILEPATH="$1"
ZIPPATH="$2"
VERSION="$3"
IS_UBUNTU=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
[[ ${IS_UBUNTU} == "Ubuntu" ]] && IS_UBUNTU=true || IS_UBUNTU=false

echo -e "[*] Detected OS: ${IS_UBUNTU}"

### Reset
echo -e "\n[*] Cleaning up previous EMBA Docker files"
if rm -rf "${FILEPATH}" ; then
  echo -e "[✓] Removed old directory"
else
  echo -e "[!!] Warning: Could not remove old directory"
fi
if rm -f "${ZIPPATH}" ; then
  echo -e "[✓] Removed old ZIP file"
else
  echo -e "[!!] Warning: Could not remove old ZIP file"
fi
if mkdir -p "${FILEPATH}" ; then
  echo -e "[✓] Created output directory\n"
else
  echo -e "[!!] ERROR: Failed to create output directory"
fi

### Copy scripts
echo -e "[*] Copying installer script"
if cp "emba_docker_installer.sh" "${FILEPATH}/installer.sh" ; then
  echo -e "[✓] Installer script copied\n"
else
  echo -e "[!!] ERROR: Failed to copy installer script"
  exit 1
fi

### Install needed tools
if ! which curl &> /dev/null; then
  echo -e "[*] Installing curl"
  apt-get update -y
  if apt-get install -y curl ; then
    echo -e "[✓] curl installed"
  else
    echo -e "[!!] ERROR: Failed to install curl"
    exit 1
  fi
else
  echo -e "[*] curl already installed"
fi

if ! which docker &> /dev/null; then
  echo -e "\n[*] Installing Docker"
  if apt-get install -y ca-certificates; then
    echo -e "[✓] ca-certificates installed"
  else
    echo -e "[!!] ERROR: Failed to install ca-certificates"
  fi
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
  if apt install -y docker-ce; then
    echo -e "[✓] Docker-ce installed"
  else
    echo -e "[!!] ERROR: Failed to install Docker-ce"
  fi
else
  echo -e "\n[*] Docker already installed"
fi

echo -e "[*] Ensuring Docker service is running"
if ! systemctl is-active --quiet docker ; then
  if systemctl start docker ; then
    echo -e "[✓] Docker service started"
  else
    echo -e "[!!] ERROR: Failed to start Docker service"
  fi
fi

if [[ "${VERSION}" == "latest" ]]; then
  echo -e "\n[*] Fetching latest EMBA version from GitHub"
  ### Find image
  EMBAVERSION=$(curl -sL https://raw.githubusercontent.com/e-m-b-a/emba/refs/heads/master/docker-compose.yml | awk -F: '/image:/ {print $NF; exit}')
else
  echo -e "\n[*] Using specified version: ${VERSION}"
  EMBAVERSION="${VERSION}"
fi

echo -e "\n[*] Pulling EMBA Docker image: embeddedanalyzer/emba:${EMBAVERSION}"
if docker pull "embeddedanalyzer/emba:${EMBAVERSION}" ; then
  echo -e "[✓] Docker image pulled successfully"
else
  echo -e "[!!] ERROR: Failed to pull Docker image"
  exit 1
fi

echo -e "\n[*] Exporting Docker image to tar archive"
if docker save -o "${FILEPATH}/emba-docker-image.tar" "embeddedanalyzer/emba:${EMBAVERSION}" ; then
  echo -e "[✓] Image exported to tar archive"
else
  echo -e "[!!] ERROR: Failed to export image"
  exit 1
fi
echo -e "[*] Setting tar archive permissions"
if chmod 755 "${FILEPATH}/emba-docker-image.tar" ; then
  echo -e "[✓] Permissions set"
else
  echo -e "[!!] ERROR: Failed to set permissions"
  exit 1
fi

echo -e "[*] Cleaning up local Docker image"
if docker image rm "embeddedanalyzer/emba:${EMBAVERSION}" ; then
  echo -e "[✓] Local image removed"
else
  echo -e "[!!] ERROR: Failed to remove local image"
  exit 1
fi

echo -e "\n[*] Creating compressed archive at: ${ZIPPATH}"
if tar czf "${ZIPPATH}" -C "${FILEPATH}" . ; then
  echo -e "[✓] Archive created successfully\n"
else
  echo -e "[!!] ERROR: Failed to create archive"
  exit 1
fi

echo -e "[✓] EMBA Docker image preparation completed successfully\n"
