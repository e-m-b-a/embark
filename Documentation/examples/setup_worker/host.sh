#!/bin/bash

# Works with Kali Linux 2025.1c: https://cdimage.kali.org/kali-2025.1c/kali-linux-2025.1c-installer-amd64.iso

if [[ $EUID -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="./WORKER_SETUP"
PKGPATH="${FILEPATH}/pkg"
EXTERNALPATH="${FILEPATH}/external"
TESTPATH="${FILEPATH}/test"
EMBAVERSION="1.5.2c"

function downloadPackage() {
	( cd "$PKGPATH" && apt-get download $(apt-cache depends --recurse --no-recommends --no-suggests \
	  --no-conflicts --no-breaks --no-replaces --no-enhances \
	  --no-pre-depends "$@" | grep "^\w") )
}

### Enable SSH to access data via sshfs
systemctl enable ssh
systemctl start ssh

mkdir -p "${FILEPATH}"

### Copy scripts
cp "installer.sh" "${FILEPATH}"
cp "uninstaller.sh" "${FILEPATH}"

mkdir "${TESTPATH}"
cp "firmware.zip" "${TESTPATH}"
cp "run_emba_test.sh" "${TESTPATH}"

### Download EMBA
apt-get update -y
apt-get install -y curl
curl -L --url https://github.com/e-m-b-a/emba/archive/refs/heads/master.tar.gz --output "${FILEPATH}/emba.tar.gz"

### Install docker apt repository
apt-get install -y ca-certificates
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y

### Download debs from https://packages.debian.org/sid/amd64/<packagename>/download
mkdir -p "${PKGPATH}"

# Needed to run EMBA:
downloadPackage docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Needed for EMBA:
downloadPackage inotify-tools
downloadPackage libnotify-bin

# Build index (for dependency tree)
apt-get install -y dpkg-dev
( cd "${PKGPATH}" && dpkg-scanpackages . ) | gzip -9c > "${PKGPATH}/Packages.gz"

### Export EMBA image
apt install -y docker-ce
systemctl start docker
docker pull "embeddedanalyzer/emba:${EMBAVERSION}"
docker save -o "${FILEPATH}/emba-docker-image.tar" "embeddedanalyzer/emba:${EMBAVERSION}"
chmod 755 "${FILEPATH}/emba-docker-image.tar"

### Download external data
mkdir -p "${EXTERNALPATH}"
if [ ! -d "${EXTERNALPATH}/nvd-json-data-feeds" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/nvd-json-data-feeds.git "${EXTERNALPATH}/nvd-json-data-feeds"
fi
if [ ! -d "${EXTERNALPATH}/EPSS-data" ]; then
	git clone --depth 1 -b main https://github.com/EMBA-support-repos/EPSS-data.git "${EXTERNALPATH}/EPSS-data"
fi

### Fake venv (packages are broken)
mkdir -p "${EXTERNALPATH}/emba_venv/bin"
touch "${EXTERNALPATH}/emba_venv/bin/activate"

echo "Preparation done"
