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

echo -e "\n[+] Starting EMBA repository download script"
echo -e "[*] Output Directory: $1"
echo -e "[*] ZIP Output Path: $2"
echo -e "[*] Version: $3\n"

FILEPATH="$1"
ZIPPATH="$2"
VERSION="$3"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] ZIP path: ${ZIPPATH}"
echo -e "[*] Version: ${VERSION}\n"

### Reset
echo -e "[*] Cleaning up previous EMBA repository files"
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
  exit 1
fi

### Copy scripts
echo -e "[*] Copying installer scripts"
if cp "emba_repo_installer.sh" "${FILEPATH}/installer.sh" ; then
  echo -e "[✓] Installer script copied"
else
  echo -e "[!!] ERROR: Failed to copy installer script"
  exit 1
fi
if cp "full_uninstaller.sh" "${FILEPATH}" ; then
  echo -e "[✓] Uninstaller script copied\n"
else
  echo -e "[!!] ERROR: Failed to copy uninstaller script"
  exit 1
fi

### Install needed tools
if ! which curl &> /dev/null; then
  echo -e "[*] Installing curl"
  if apt-get update -y ; then
    echo -e "[✓] Package list updated"
  else
    echo -e "[!!] ERROR: Failed to update package list"
    exit 1
  fi
  if apt-get install -y curl ; then
    echo -e "[✓] curl installed"
  else
    echo -e "[!!] ERROR: Failed to install curl"
    exit 1
  fi
else
  echo -e "[*] curl already installed"
fi

### Download EMBA
if [ "${VERSION}" = "latest" ]; then
  echo -e "\n[*] Downloading latest EMBA repository from GitHub"
  if curl -L --url https://github.com/e-m-b-a/emba/archive/refs/heads/master.tar.gz --output "${FILEPATH}/emba.tar.gz" ; then
    echo -e "[✓] Repository downloaded"
  else
    echo -e "[!!] ERROR: Failed to download repository"
    exit 1
  fi
  echo -e "[*] Fetching latest commit hash"
  if sha=$(git ls-remote https://github.com/e-m-b-a/emba HEAD | awk '{print $1}') ; then
    echo -e "[✓] Commit hash retrieved: ${sha}"
  else
    echo -e "[!!] ERROR: Failed to fetch commit hash"
    exit 1
  fi
  if echo "${sha} N/A" > "${FILEPATH}/git-head-meta" ; then
    echo -e "[✓] Metadata saved"
  else
    echo -e "[!!] ERROR: Failed to save metadata"
    exit 1
  fi
else
  echo -e "\n[*] Downloading EMBA version: ${VERSION}"
  if curl -L --url "https://github.com/e-m-b-a/emba/archive/${VERSION}.tar.gz" --output "${FILEPATH}/emba.tar.gz" ; then
    echo -e "[✓] Repository downloaded"
  else
    echo -e "[!!] ERROR: Failed to download repository"
    exit 1
  fi
  if echo "${VERSION} N/A" > "${FILEPATH}/git-head-meta" ; then
    echo -e "[✓] Version metadata saved"
  else
    echo -e "[!!] ERROR: Failed to save metadata"
    exit 1
  fi
fi

echo -e "\n[*] Creating compressed archive at: ${ZIPPATH}"
if tar czf "${ZIPPATH}" -C "${FILEPATH}" . ; then
  echo -e "[✓] Archive created successfully\n"
else
  echo -e "[!!] ERROR: Failed to create archive"
  exit 1
fi

echo -e "[✓] EMBA repository download completed successfully\n"
