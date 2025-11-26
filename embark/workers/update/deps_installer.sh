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
# Contributor(s): Luka Dekanozishvili, Benedikt Kuehne

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting dependency installation script on offline worker"
echo -e "[*] Current directory: $(pwd)\n"

FILEPATH="."
PKGPATH="${FILEPATH}/pkg"
EMBAPACKAGEPATH="/usr/local/EMBA_PACKAGES"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] Package path: ${PKGPATH}"
echo -e "[*] EMBA package path: ${EMBAPACKAGEPATH}\n"

# Remove online sources as machine is offline
echo -e "[*] Disabling online APT sources (offline mode)"
if sed -i 's|^deb http|# deb http|' /etc/apt/sources.list ; then
  echo -e "[✓] HTTP sources disabled"
else
  echo -e "[!!] Warning: Could not disable HTTP sources"
fi
if sed -i 's|^deb https|# deb https|' /etc/apt/sources.list ; then
  echo -e "[✓] HTTPS sources disabled"
else
  echo -e "[!!] Warning: Could not disable HTTPS sources"
fi

echo -e "\n[*] Removing Ubuntu 24.04 sources"
if rm -f /etc/apt/sources.list.d/ubuntu.sources ; then
  echo -e "[✓] Ubuntu sources removed\n"
else
  echo -e "[!!] Warning: Could not remove Ubuntu sources\n"
fi

# Reset
echo -e "[*] Cleaning up previous EMBA package installation"
if rm -rf "${EMBAPACKAGEPATH}" ; then
  echo -e "[✓] Previous packages removed\n"
else
  echo -e "[!!] Warning: Could not remove previous packages\n"
fi

# Register index
echo -e "[*] Copying packages to system location"
if cp -r "${PKGPATH}" "${EMBAPACKAGEPATH}" ; then
  echo -e "[✓] Packages copied"
else
  echo -e "[!!] ERROR: Failed to copy packages"
  exit 1
fi
echo -e "[*] Setting package permissions"
if chown -R _apt:root "${EMBAPACKAGEPATH}" ; then
  echo -e "[✓] Permissions set\n"
else
  echo -e "[!!] ERROR: Failed to set permissions"
  exit 1
fi

if ! grep -q "${EMBAPACKAGEPATH}" /etc/apt/sources.list; then
  echo -e "[*] Registering local package index in APT sources"
  if echo "deb [trusted=yes] file:${EMBAPACKAGEPATH} ./" | tee -a /etc/apt/sources.list ; then
    echo -e "[✓] Local package source registered"
  else
    echo -e "[!!] ERROR: Failed to register package source"
    exit 1
  fi
else
  echo -e "[*] Local package source already registered"
fi

echo -e "\n[*] Updating package index"
if apt-get update -y ; then
  echo -e "[✓] Package index updated\n"
else
  echo -e "[!!] ERROR: Failed to update package index"
  exit 1
fi

echo -e "[*] Installing Docker packages (docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin, docker-compose-plugin)"
if apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin ; then
  echo -e "[✓] Docker packages installed"
else
  echo -e "[!!] ERROR: Failed to install Docker packages"
  exit 1
fi

echo -e "[*] Installing inotify-tools"
if apt-get install -y inotify-tools ; then
  echo -e "[✓] inotify-tools installed"
else
  echo -e "[!!] ERROR: Failed to install inotify-tools"
  exit 1
fi

echo -e "[*] Installing libnotify-bin"
if apt-get install -y libnotify-bin ; then
  echo -e "[✓] libnotify-bin installed"
else
  echo -e "[!!] ERROR: Failed to install libnotify-bin"
  exit 1
fi

echo -e "[*] Installing p7zip-full"
if apt-get install -y p7zip-full ; then
  echo -e "[✓] p7zip-full installed"
else
  echo -e "[!!] ERROR: Failed to install p7zip-full"
  exit 1
fi

echo -e "\n[*] Configuring Docker service"
if systemctl enable docker ; then
  echo -e "[✓] Docker enabled at boot"
else
  echo -e "[!!] ERROR: Failed to enable Docker"
  exit 1
fi
if systemctl start docker ; then
  echo -e "[✓] Docker service started"
else
  echo -e "[!!] ERROR: Failed to start Docker service"
  exit 1
fi

echo -e "\n[✓] Dependency installation completed successfully\n"
