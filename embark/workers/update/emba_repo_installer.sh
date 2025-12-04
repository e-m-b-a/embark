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

echo -e "\n[+] Starting EMBA repository installation on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

FILEPATH="."
INSTALLPATH="/root"
EXTERNALPATH="${INSTALLPATH}/emba/external"
EMBAMASTER="${INSTALLPATH}/emba-master"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] Installation path: ${INSTALLPATH}"
echo -e "[*] External path: ${EXTERNALPATH}"
echo -e "[*] Temporary master path: ${EMBAMASTER}\n"

echo -e "[*] Cleaning up previous EMBA master directory"
if rm -rf "${EMBAMASTER}" ; then
  echo -e "[✓] Previous directory removed"
else
  echo -e "[!!] Warning: Could not remove previous directory"
fi
echo -e "[*] Creating temporary EMBA master directory"
if mkdir "${EMBAMASTER}" ; then
  echo -e "[✓] Directory created"
else
  echo -e "[!!] ERROR: Failed to create directory"
  exit 1
fi
echo -e "[*] Extracting EMBA repository archive"
if tar -xvzf "${FILEPATH}/emba.tar.gz" -C "${EMBAMASTER}" --strip-components 1 ; then
  echo -e "[✓] Archive extracted successfully\n"
else
  echo -e "[!!] ERROR: Failed to extract archive"
  exit 1
fi
if [ -d "${EXTERNALPATH}" ]; then
  echo -e "[*] Copying external files from previous EMBA installation"
  if cp -r "${EXTERNALPATH}" "${EMBAMASTER}" ; then
    echo -e "[✓] External files copied\n"
  else
    echo -e "[!!] ERROR: Failed to copy external files"
    exit 1
  fi
else
  echo -e "[*] No previous external files found\n"
fi

echo -e "[*] Removing old EMBA installation"
if rm -rf "${INSTALLPATH}/emba" ; then
  echo -e "[✓] Old installation removed"
else
  echo -e "[!!] Warning: Could not remove old installation"
fi
echo -e "[*] Moving EMBA master to final location"
if mv "${EMBAMASTER}" "${INSTALLPATH}/emba" ; then
  echo -e "[✓] EMBA moved to ${INSTALLPATH}/emba"
else
  echo -e "[!!] ERROR: Failed to move EMBA directory"
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
