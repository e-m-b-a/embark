#!/bin/bash

FILEPATH="/mnt/VM/home/root/WORKER_SETUP"
PKGPATH="${FILEPATH}/pkg"
EXTERNAL="${FILEPATH}/external"

### Download EMBA
curl -L --url https://github.com/e-m-b-a/emba/archive/refs/heads/master.tar.gz --output "${FILEPATH}/emba.tar.gz"

### Download debs from https://packages.debian.org/sid/amd64/<packagename>/download
mkdir -p "${PKGPATH}"

# docker-ce needs iptables
curl -L --url http://ftp.de.debian.org/debian/pool/main/i/iptables/libip4tc2_1.8.11-2_amd64.deb --output "${PKGPATH}/libip4.deb"
curl -L --url http://ftp.de.debian.org/debian/pool/main/i/iptables/libip6tc2_1.8.11-2_amd64.deb --output "${PKGPATH}/libip6.deb"
curl -L --url http://ftp.de.debian.org/debian/pool/main/libn/libnetfilter-conntrack/libnetfilter-conntrack3_1.1.0-1_amd64.deb --output "${PKGPATH}/libnetfilter.deb"
curl -L --url http://ftp.de.debian.org/debian/pool/main/libn/libnfnetlink/libnfnetlink0_1.0.2-3_amd64.deb --output "${PKGPATH}/libnfnetlink.deb"
curl -L --url http://ftp.de.debian.org/debian/pool/main/i/iptables/iptables_1.8.11-2_amd64.deb --output "${PKGPATH}/iptables.deb"

# docker-ce, docker-ce-cli, containered.io, docker-buildx-plugin, docker-compose-plugin
curl -L --url https://download.docker.com/linux/debian/dists/trixie/pool/stable/amd64/containerd.io_1.7.27-1_amd64.deb --output "${PKGPATH}/containered.deb"
curl -L --url https://download.docker.com/linux/debian/dists/trixie/pool/stable/amd64/docker-buildx-plugin_0.23.0-1~debian.13~trixie_amd64.deb --output "${PKGPATH}/docker-buildx-plugin.deb"
curl -L --url https://download.docker.com/linux/debian/dists/trixie/pool/stable/amd64/docker-ce-cli_28.1.1-1~debian.13~trixie_amd64.deb --output "${PKGPATH}/docker-ce-cli.deb"
curl -L --url https://download.docker.com/linux/debian/dists/trixie/pool/stable/amd64/docker-ce_28.1.1-1~debian.13~trixie_amd64.deb --output "${PKGPATH}/docker-ce.deb"
curl -L --url https://download.docker.com/linux/debian/dists/trixie/pool/stable/amd64/docker-compose-plugin_2.35.1-1~debian.13~trixie_amd64.deb --output "${PKGPATH}/docker-compose-plugin.deb"

# Needed for EMBA (inotify):
curl -L --url http://ftp.de.debian.org/debian/pool/main/i/inotify-tools/inotify-tools_4.23.9.0-2+b1_amd64.deb --output "${PKGPATH}/inotify.deb"
curl -L --url http://ftp.de.debian.org/debian/pool/main/i/inotify-tools/libinotifytools0_4.23.9.0-2+b1_amd64.deb --output "${PKGPATH}/libinotify.deb"

### Export EMBA image
# docker save -o "${FILEPATH}/emba-docker-image.tar" embeddedanalyzer/emba

### Download external data
mkdir -p "${EXTERNAL}"
if [ ! -d "${EXTERNAL}/nvd-json-data-feeds" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/nvd-json-data-feeds.git "${EXTERNAL}/nvd-json-data-feeds"
fi
if [ ! -d "${EXTERNAL}/EPSS-data" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/EPSS-data.git "${EXTERNAL}/EPSS-data"
fi

### Fake venv (no packages have to be installed)
mkdir -p "${EXTERNAL}/emba_venv/bin"
touch "${EXTERNAL}/emba_venv/bin/activate"
