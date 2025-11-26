#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
# Copyright 2025 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): ClProsser, SirGankalot
# Contributor(s): Luka Dekanozishvili, ashiven, Benedikt Kuehne
#
# Description: Prepares dependency packages on the host system for worker update

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting dependency package preparation script"
echo -e "[*] Dependency Directory: $1"
echo -e "[*] ZIP Output Path: $2"
echo -e "[*] Version: $3"
echo -e "[*] Dependencies Cache: $4\n"

FILEPATH="$1"   # Directory to store dependency packages
ZIPPATH="$2"  # Optional: Path to store tar.gz of dependency packages
VERSION="$3"  # Version of dependencies to download (or "latest")
DEPSCACHE="$4"  # Optional: Path to cache previously downloaded dependencies

PKGPATH="${FILEPATH}/pkg"
IS_UBUNTU=$(awk -F= '/^NAME/{gsub(/"/, "", $2); print $2}' /etc/os-release)
[[ ${IS_UBUNTU} == "Ubuntu" ]] && IS_UBUNTU=true || IS_UBUNTU=false

echo -e "[*] Detected OS: ${IS_UBUNTU}"

function downloadPackage() {
  echo -e "[*] Downloading packages: $@"
  # shellcheck disable=SC2046
  if ( cd "${PKGPATH}" && apt-get download $(apt-cache depends --recurse --no-recommends --no-suggests \
    --no-conflicts --no-breaks --no-replaces --no-enhances \
    --no-pre-depends "$@" | grep "^\w") ); then
    echo -e "[✓] Packages downloaded successfully"
  else
    echo -e "[!!] ERROR: Failed to download packages"
  fi
}

### Reset
echo -e "\n[*] Cleaning up previous dependency files"
if rm -rf "${FILEPATH}" ; then
  echo -e "[✓] Removed old filepath"
else
  echo -e "[!!] Warning: Could not remove old filepath"
fi

if [ -n "${ZIPPATH}" ]; then
  if rm -f "${ZIPPATH}" ; then
    echo -e "[✓] Removed old ZIP file"
  else
    echo -e "[!!] Warning: Could not remove old ZIP file"
  fi
fi

if mkdir -p "${FILEPATH}" ; then
  echo -e "[✓] Created dependency directory\n"
else
  echo -e "[!!] ERROR: Failed to create dependency directory"
  exit 1
fi

### Copy scripts
echo -e "[*] Copying installer script"
if cp "deps_installer.sh" "${FILEPATH}/installer.sh" ; then
  echo -e "[✓] Installer script copied"
else
  echo -e "[!!] ERROR: Failed to copy installer script"
  exit 1
fi

echo -e "\n[*] Updating package list"
if apt-get update -y ; then
  echo -e "[✓] Package list updated\n"
else
  echo -e "[!!] ERROR: Failed to update package list"
  exit 1
fi

if [ "${VERSION}" = "latest" ] || [ ! -d "${DEPSCACHE}/pkg" ]; then
  echo -e "[*] Using latest version or cache not available"
  echo -e "[*] Preparing to download dependencies\n"
  ### Add some required sources if they haven't been added yet
  if [ ! -f /etc/apt/sources.list.d/embark.list ]; then
    echo -e "[*] Adding required APT sources"
    echo 'deb http://archive.ubuntu.com/ubuntu jammy main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://security.ubuntu.com/ubuntu jammy-security main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://archive.ubuntu.com/ubuntu jammy-updates main universe restricted multiverse' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    echo 'deb http://archive.ubuntu.com/ubuntu focal main universe' | tee -a /etc/apt/sources.list.d/embark.list >/dev/null
    if apt-get update -y ; then
      echo -e "[✓] APT sources added and updated\n"
    else
      echo -e "[!!] ERROR: Failed to add APT sources"
      exit 1
    fi
  else
    echo -e "[*] APT sources already configured\n"
  fi

  ### Install needed tools
  if ! which curl &> /dev/null; then
    echo -e "[*] Installing curl"
    if apt-get install -y curl ; then
      echo -e "[✓] curl installed"
    else
      echo -e "[!!] ERROR: Failed to install curl"
      exit 1
    fi
  else
    echo -e "[*] curl already installed"
  fi

  if ! which dpkg-scanpackages &> /dev/null; then
    echo -e "[*] Installing dpkg-dev"
    if apt-get install -y dpkg-dev ; then
      echo -e "[✓] dpkg-dev installed"
    else
      echo -e "[!!] ERROR: Failed to install dpkg-dev"
      exit 1
    fi
  else
    echo -e "[*] dpkg-dev already installed"
  fi

  if ! which docker &> /dev/null; then
    echo -e "\n[*] Installing Docker"
    apt-get install -y ca-certificates && echo -e "[✓] ca-certificates installed" || { echo -e "[!!] ERROR: Failed to install ca-certificates"; exit 1; }
    install -m 0755 -d /etc/apt/keyrings

    if [ ! -f /etc/apt/sources.list.d/docker.list ]; then
      echo -e "[*] Adding Docker repository"
      if [ "${IS_UBUNTU}" = true ] ; then
        echo -e "[*] Downloading Ubuntu Docker GPG key"
    if curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc ; then
      echo -e "[✓] Docker GPG key downloaded"
    else
      echo -e "[!!] ERROR: Failed to download Docker GPG key"
      exit 1
    fi
	# shellcheck source=/dev/null
	echo -e "[*] Adding Ubuntu Docker repository"
	echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
	  $(. /etc/os-release && echo "${UBUNTU_CODENAME}:-${VERSION_CODENAME}") stable" | \
      if tee /etc/apt/sources.list.d/docker.list > /dev/null ; then
        echo -e "[✓] Docker repository added"
      else
        echo -e "[!!] ERROR: Failed to add Docker repository"
        exit 1
      fi
      else
        echo -e "[*] Downloading Debian Docker GPG key"
	curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && echo -e "[✓] Docker GPG key downloaded" || { echo -e "[!!] ERROR: Failed to download Docker GPG key"; exit 1; }
	echo -e "[*] Adding Debian Docker repository"
	echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" | \
	  tee /etc/apt/sources.list.d/docker.list > /dev/null && echo -e "[✓] Docker repository added" || { echo -e "[!!] ERROR: Failed to add Docker repository"; exit 1; }
      fi

      chmod a+r /etc/apt/keyrings/docker.asc
      echo -e "[*] Updating package list for Docker"
      if apt-get update -y ; then
        echo -e "[✓] Package list updated"
      else
        echo -e "[!!] ERROR: Failed to update package list"
        exit 1
      fi
    else
      echo -e "[*] Docker repository already configured"
    fi

    echo -e "[*] Installing Docker packages"
    if apt-get install -y docker-ce ; then
      echo -e "[✓] Docker installed"
    else
      echo -e "[!!] ERROR: Failed to install Docker"
      exit 1
    fi
  else
    echo -e "[*] Docker already installed"
  fi
  
  echo -e "[*] Ensuring Docker service is running"
  if ! systemctl is-active --quiet docker ; then
    if systemctl start docker ; then
      echo -e "[✓] Docker service started"
    else
      echo -e "[!!] ERROR: Failed to start Docker service"
      exit 1
    fi
  fi

  ### Download debs from https://packages.debian.org/sid/amd64/<packagename>/download
  echo -e "\n[*] Creating package directory"
  if mkdir -p "${PKGPATH}" ; then
    echo -e "[✓] Package directory created\n"
  else
    echo -e "[!!] ERROR: Failed to create package directory"
    exit 1
  fi

  # Needed to run EMBA:
  echo -e "[*] Downloading Docker packages (docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin, docker-compose-plugin)"
  downloadPackage docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Needed for EMBA:
  echo -e "[*] Downloading inotify-tools"
  downloadPackage inotify-tools
  echo -e "[*] Downloading libnotify-bin"
  downloadPackage libnotify-bin
  echo -e "[*] Downloading p7zip-full"
  downloadPackage p7zip-full

  echo -e "\n[*] Building Debian package index"
  if ( cd "${PKGPATH}" && dpkg-scanpackages . ) | gzip -9c > "${PKGPATH}/Packages.gz" ; then
    echo -e "[✓] Package index created"
  else
    echo -e "[!!] ERROR: Failed to create package index"
    exit 1
  fi
else
  echo -e "\n[*] Using cached dependencies from: ${DEPSCACHE}/pkg"
  if cp -rf "${DEPSCACHE}/pkg" "${PKGPATH}" ; then
    echo -e "[✓] Dependencies copied from cache\n"
  else
    echo -e "[!!] ERROR: Failed to copy cached dependencies"
    exit 1
  fi
fi

if [ -n "${ZIPPATH}" ]; then
  echo -e "[*] Creating compressed archive at: ${ZIPPATH}"
  if tar czf "${ZIPPATH}" -C "${FILEPATH}" . ; then
    echo -e "[✓] Archive created successfully\n"
  else
    echo -e "[!!] ERROR: Failed to create archive"
    exit 1
  fi
fi

echo -e "[✓] Dependency preparation completed successfully\n"
