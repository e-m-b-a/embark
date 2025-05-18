#!/bin/bash

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
