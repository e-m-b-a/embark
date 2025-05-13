#!/bin/bash

FILEPATH="/home/root/WORKER_SETUP"
PKGPATH="${FILEPATH}/pkg"
EXTERNALPATH="${FILEPATH}/external"
INSTALLPATH="/root"

# Install iptables (needed by docker)
dpkg -i "${PKGPATH}/libip4.deb"
dpkg -i "${PKGPATH}/libip6.deb"
dpkg -i "${PKGPATH}/libnfnetlink.deb"
dpkg -i "${PKGPATH}/libnetfilter.deb"
dpkg -i "${PKGPATH}/iptables.deb"

# Install docker
dpkg -i "${PKGPATH}/containered.deb" "${PKGPATH}/docker-buildx-plugin.deb" "${PKGPATH}/docker-ce-cli.deb" "${PKGPATH}/docker-ce.deb" "${PKGPATH}/docker-compose-plugin.deb"

# Install inotify
dpkg -i "${PKGPATH}/libinotify.deb"
dpkg -i "${PKGPATH}/inotify.deb"

# Load EMBA image
docker image load -i "${FILEPATH}/emba-docker-image.tar"

# Install EMBA
tar -xvzf "${FILEPATH}/emba.tar.gz" -C "${INSTALLPATH}"
mv "${INSTALLPATH}/emba-master/" "${INSTALLPATH}/emba"

# Setup external
cp -r "${EXTERNALPATH}" "${INSTALLPATH}/emba"

# Fake notify-send (not used by EMBArk)
if [ ! -f "/bin/notify-send" ] ; then
	touch "/bin/notify-send"
	chmod +x "/bin/notify-send"
fi
