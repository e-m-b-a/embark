#!/bin/bash

FILEPATH="/home/clprosser/WORKER_SETUP"
PKGPATH="${FILEPATH}/pkg"
INSTALLPATH="/root"

rm -rf "${INSTALLPATH}/emba"
rm -rf "${INSTALLPATH}/emba-master"

docker system prune -af

pkglist=("docker-compose-plugin" "docker-ce" "docker-ce-cli" "docker-buildx-plugin" "containered" "iptables" "libnetfilter" "libnfnetlink" "libip4" "libip6")
for package in "${pkglist[@]}"
do
	dpkg -r $(dpkg -f "${PKGPATH}/${package}.deb" Package)
done
