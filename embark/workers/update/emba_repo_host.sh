#!/bin/bash

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

set -e
cd "$(dirname "${0}")"

if [[ "${EUID}" -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting EMBA repository archive creationscript"
echo -e "[*] Output Directory: ${1}"
echo -e "[*] ZIP Output Path: ${2}"
echo -e "[*] Version: ${3}\n"
echo -e "[*] EMBA location: ${4}\n"

FILEPATH="${1}"
ZIPPATH="${2}"
VERSION="${3}"
LOCATION="${4}"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] ZIP path: ${ZIPPATH}"
echo -e "[*] Version: ${VERSION}\n"
echo -e "[*] Location: ${LOCATION}\n"

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

### Create archive
echo -e "\n[*] Create archive of EMBA repository from ${VERSION}"
if tar --exclude="${LOCATION}/external" -czf "${FILEPATH}/emba.tar.gz" "${LOCATION}" ; then  # TODO check implement propper tar with errorhandling # maybe exclude external dir
  echo -e "[✓] Archive created successfully\n"
else
  echo -e "[!!] ERROR: Failed to create archive"
  exit 1
fi
echo -e "[✓] Repository archived\n"

echo -e "[*] Fetching latest commit hash"
if sha="$(git rev-parse HEAD)" ; then
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

echo -e "[✓] EMBA repository ready for transfer\n"
