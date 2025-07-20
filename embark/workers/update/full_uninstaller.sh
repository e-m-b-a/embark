#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): ClProsser, SirGankalot
# Contributor(s): Luka Dekanozishvili

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

INSTALLPATH="/root"
EMBAPACKAGEPATH="/usr/local/EMBA_PACKAGES"

rm -rf "${INSTALLPATH}/emba"
rm -rf "${INSTALLPATH}/emba-master"
rm -rf "${INSTALLPATH}/firmware"
rm -rf "${INSTALLPATH}/emba_logs"

if command -v docker >/dev/null 2>&1; then
	docker system prune -af

	apt-get autoremove --purge -y libnotify-bin
	apt-get autoremove --purge -y inotify-tools
	apt-get autoremove --purge -y p7zip-full
	apt-get autoremove --purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

rm -rf "${EMBAPACKAGEPATH}"

sed -i 's|^# deb http|deb http|' /etc/apt/sources.list
sed -i 's|^# deb https|deb https|' /etc/apt/sources.list

grep -v "${EMBAPACKAGEPATH}" /etc/apt/sources.list > "${INSTALLPATH}/temp"
mv "${INSTALLPATH}/temp" /etc/apt/sources.list
