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

echo -e "\n[+] Starting EMBA Docker image installation on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

FILEPATH="."

echo -e "[*] Image file path: ${FILEPATH}\n"

# Reset
echo -e "[*] Ensuring Docker service is running"
if ! systemctl is-active --quiet docker ; then
	if systemctl start docker ; then
		echo -e "[✓] Docker service started"
	else
		echo -e "[!!] ERROR: Failed to start Docker service"
	fi
fi

echo -e "[*] Cleaning up Docker system (removing unused images and containers)"
if docker system prune -af ; then
	echo -e "[✓] Docker system cleaned\n"
else
	echo -e "[!!] ERROR: Failed to clean Docker system"
fi

# Load EMBA image
echo -e "[*] Loading EMBA Docker image from: ${FILEPATH}/emba-docker-image.tar"
if docker image load -i "${FILEPATH}/emba-docker-image.tar" ; then
	echo -e "[✓] Docker image loaded successfully\n"
else
	echo -e "[!!] ERROR: Failed to load Docker image"
	exit 1
fi

echo -e "[✓] EMBA Docker image installation completed successfully\n"
