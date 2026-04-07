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
# Description: Script to install the EMBA repository on an offline worker. 
#   This script is intended to be run on the offline worker after the EMBA repository archive has been transferred to it.
# Note: Destination is $WORKER_EMBA_ROOT
set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting EMBA repository installation on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

FILEPATH="."
INSTALLPATH="/root"
EXTERNALPATH="${INSTALLPATH}/emba/external"
EMBAMASTER="${INSTALLPATH}/emba-master"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] Installation path: ${INSTALLPATH}"
echo -e "[*] External path: ${EXTERNALPATH}"

cd "$(dirname "${INSTALLPATH}")"

# overwrite all - no external dir
echo -e "[*] Extracting EMBA repository archive"
if tar -xvzf "${FILEPATH}/emba.tar.gz" --strip-components 1 --overwrite ; then
  echo -e "[✓] Archive extracted successfully\n"
else
  echo -e "[!!] ERROR: Failed to extract archive"
  exit 1
fi

echo -e "[*] Copying uninstaller script"
if cp "${FILEPATH}/full_uninstaller.sh" "${INSTALLPATH}/emba" ; then
  echo -e "[✓] Uninstaller copied"
else
  echo -e "[!!] ERROR: Failed to copy uninstaller"
  exit 1
fi
echo -e "[*] Copying git metadata"
if cp "${FILEPATH}/git-head-meta" "${INSTALLPATH}/emba" ; then
  echo -e "[✓] Metadata copied\n"
else
  echo -e "[!!] ERROR: Failed to copy metadata"
  exit 1
fi
echo -e "[✓] EMBA repository installation completed successfully\n"
