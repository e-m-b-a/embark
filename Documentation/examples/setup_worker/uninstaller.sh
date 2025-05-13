#!/bin/bash

FILEPATH="/home/root/WORKER_SETUP"
PKGPATH="${FILEPATH}/pkg"
INSTALLPATH="/root"

rm -rf "${INSTALLPATH}/emba"
rm -rf "${INSTALLPATH}/emba-master"

docker system prune -af

pkglist=("docker-compose-plugin" "docker-ce" "docker-ce-cli" "docker-buildx-plugin" "containered" "iptables" "libnetfilter" "libnfnetlink" "libip4" "libip6" "inotify" "libinotify" )
for package in "${pkglist[@]}"
do
	dpkg -r $(dpkg -f "${PKGPATH}/${package}.deb" Package)
done

if [ ! -s "/bin/notify-send" ] ; then
	rm "/bin/notify-send"
fi
