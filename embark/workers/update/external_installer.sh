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

################################################################################
# DESCRIPTION:
# This script installs external security data (NVD and EPSS databases) on an
# offline EMBA worker system. It replaces the existing external data directory
# with the new data that was prepared by external_host.sh.
#
# This script is designed to run on systems without internet access, where
# the external data archive has been transferred.
#
# USAGE:
#   ./external_installer.sh
#   (Run from the directory containing the extracted external data archive)
#
# REQUIREMENTS:
#   - Must be run as root
#   - EMBA must be installed at /root/emba
#   - External data must be extracted in ./external/ subdirectory
################################################################################

set -e
cd "$(dirname "$0")"

# Ensure script runs with root privileges (required for file operations in /root)
if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting external data installation on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

# Define paths for the installation process
# Current directory should contain the extracted external data archive
FILEPATH="${PWD}"
# Path to the external data directory (contains NVD and EPSS data)
EXTERNALPATH="${FILEPATH}/external"
# Standard EMBA installation path
EMBAPATH="/root/emba"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] External data path: ${EXTERNALPATH}"
echo -e "[*] EMBA installation path: ${EMBAPATH}\n"

# VALIDATION PHASE: Ensure EMBA is installed before proceeding
echo -e "[*] Checking if EMBA directory exists"
if [ ! -d "${EMBAPATH}" ]; then
  echo -e "[!!] ERROR: EMBA directory not found at ${EMBAPATH}"
  exit 1
fi
echo -e "[✓] EMBA directory found\n"

# CLEANUP PHASE: Remove existing external data to ensure clean installation
echo -e "[*] Removing old external data from EMBA installation"
if rm -rf "${EMBAPATH}/external"; then
  echo -e "[✓] Old external data removed"
else
  echo -e "[!!] Warning: Could not remove old external data"
fi

# INSTALLATION PHASE: Copy new external data to EMBA directory
echo -e "[*] Installing new external data"
if cp -r "${EXTERNALPATH}" "${EMBAPATH}"; then
  echo -e "[✓] External data installed successfully\n"
else
  echo -e "[!!] ERROR: Failed to install external data"
  exit 1
fi

echo -e "[✓] External data installation completed successfully\n"
