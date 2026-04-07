#!/bin/bash
# shellcheck disable=SC2031
# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
# Copyright 2025-2026 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): ClProsser, SirGankalot
# Contributor(s): Benedikt Kuehne

# TODO here we just take the image id from the updater and put it into emba-docker-image.tar , remove the rest when switching to updater

set -e
cd "$(dirname "${0}")"

if [[ "${EUID}" -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting EMBA Docker image preparation script"
echo -e "[*] Output Directory: ${1}"
echo -e "[*] ZIP Output Path: ${2}"
echo -e "[*] Image id: ${3}\n"

FILEPATH="${1}"
ZIPPATH="${2}"
IMAGE_ID="${3}"

echo -e "[*] File path: ${FILEPATH}\n"
echo -e "[*] ZIP path: ${ZIPPATH}\n"
echo -e "[*] Image ID: ${IMAGE_ID}\n"

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

echo -e "[*] Ensuring Docker service is running"
if ! systemctl is-active --quiet docker ; then
  if systemctl start docker ; then
    echo -e "[✓] Docker service started"
  else
    echo -e "[!!] ERROR: Failed to start Docker service"
  fi
fi

echo -e "\n[*] Exporting Docker image to tar archive"
if docker save -o "${FILEPATH}/emba-docker-image.tar" "${IMAGE_ID}" ; then
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

echo -e "\n[*] Creating compressed archive at: ${ZIPPATH}"
if tar czf "${ZIPPATH}" -C "${FILEPATH}" . ; then
  echo -e "[✓] Archive created successfully\n"
else
  echo -e "[!!] ERROR: Failed to create archive"
  exit 1
fi

echo -e "[✓] EMBA Docker image preparation completed successfully\n"
