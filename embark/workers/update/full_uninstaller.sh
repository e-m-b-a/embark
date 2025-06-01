#!/bin/bash

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

docker system prune -af

apt-get autoremove --purge -y libnotify-bin
apt-get autoremove --purge -y inotify-tools
apt-get autoremove --purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

rm -rf "${EMBAPACKAGEPATH}"

sed -i 's|^# deb http|deb http|' /etc/apt/sources.list
sed -i 's|^# deb https|deb https|' /etc/apt/sources.list

grep -v "${EMBAPACKAGEPATH}" /etc/apt/sources.list > temp
mv temp /etc/apt/sources.list
