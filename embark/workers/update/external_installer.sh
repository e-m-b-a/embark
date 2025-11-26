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

echo -e "\n[+] Starting external data installation on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

FILEPATH="."
EXTERNALPATH="${FILEPATH}/external"
EMBAPATH="/root/emba"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] External data path: ${EXTERNALPATH}"
echo -e "[*] EMBA installation path: ${EMBAPATH}\n"

echo -e "[*] Checking if EMBA directory exists"
[ -d "${EMBAPATH}" ] || { echo -e "[!!] ERROR: EMBA directory not found at ${EMBAPATH}"; exit 1; }
echo -e "[✓] EMBA directory found\n"

echo -e "[*] Removing old external data from EMBA installation"
if rm -rf "${EMBAPATH}/external"; then
  echo -e "[✓] Old external data removed"
else
  echo -e "[!!] Warning: Could not remove old external data"
fi

echo -e "[*] Installing new external data"
if cp -r "${EXTERNALPATH}" "${EMBAPATH}"; then
  echo -e "[✓] External data installed successfully\n"
else
  echo -e "[!!] ERROR: Failed to install external data"
  exit 1
fi

echo -e "[✓] External data installation completed successfully\n"
