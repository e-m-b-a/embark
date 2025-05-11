#!/bin/bash

FILEPATH="/home/clprosser/WORKER_SETUP"
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

dpkg -i "${PKGPATH}/python-packaging.deb"
dpkg -i "${PKGPATH}/python-wheel.deb"
dpkg -i "${PKGPATH}/python-pip.deb"

# Load EMBA image
docker image load -i "${FILEPATH}/emba-docker-image.tar"

# Install EMBA
tar -xvzf "${FILEPATH}/emba.tar.gz" -C "${INSTALLPATH}"
mv "${INSTALLPATH}/emba-master/" "${INSTALLPATH}/emba"

# Setup external
cp -r "${EXTERNALPATH}" "${INSTALLPATH}/emba"
