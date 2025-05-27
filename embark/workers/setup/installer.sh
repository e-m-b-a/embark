#!/bin/bash

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="."
PKGPATH="${FILEPATH}/pkg"
EXTERNALPATH="${FILEPATH}/external"
INSTALLPATH="/root"
EMBAPACKAGEPATH="/usr/local/EMBA_PACKAGES"

# Remove online sources as machine is offline
sed -i 's|^deb http|# deb http|' /etc/apt/sources.list
sed -i 's|^deb https|# deb https|' /etc/apt/sources.list

# Remove ubuntu 24.04 sources
rm /etc/apt/soruces.list.d/ubuntu.sources

# Register index
cp -r "${PKGPATH}" "${EMBAPACKAGEPATH}"
chown -R _apt:root "${EMBAPACKAGEPATH}"
echo "deb [trusted=yes] file:${EMBAPACKAGEPATH} ./" | tee -a /etc/apt/sources.list
apt-get update -y

apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

apt-get install -y inotify-tools
apt-get install -y libnotify-bin

# Load EMBA image
systemctl enable docker
systemctl start docker
docker image load -i "${FILEPATH}/emba-docker-image.tar"

# Install EMBA
tar -xvzf "${FILEPATH}/emba.tar.gz" -C "${INSTALLPATH}"
mv "${INSTALLPATH}/emba-master/" "${INSTALLPATH}/emba"

# Setup external
cp -r "${EXTERNALPATH}" "${INSTALLPATH}/emba"

echo "Installation done"
