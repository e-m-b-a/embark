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

echo -e "\n[+] Starting EMBA full uninstaller"
echo -e "[*] Current directory: $(pwd)\n"

INSTALLPATH="/root"
EMBAPACKAGEPATH="/usr/local/EMBA_PACKAGES"

echo -e "[*] Installation path: ${INSTALLPATH}"
echo -e "[*] Package path: ${EMBAPACKAGEPATH}\n"

echo -e "[*] Removing EMBA installation directories"
if rm -rf "${INSTALLPATH}/emba"; then
  echo -e "[✓] EMBA directory removed"
else
  echo -e "[!!] Warning: Could not remove EMBA directory"
fi

if rm -rf "${INSTALLPATH}/emba-master"; then
  echo -e "[✓] EMBA-master directory removed"
else
  echo -e "[!!] Warning: Could not remove EMBA-master directory"
fi

if rm -rf "${INSTALLPATH}/firmware"; then
  echo -e "[✓] Firmware directory removed"
else
  echo -e "[!!] Warning: Could not remove firmware directory"
fi

if rm -rf "${INSTALLPATH}/emba_logs"; then
  echo -e "[✓] EMBA logs directory removed\n"
else
  echo -e "[!!] Warning: Could not remove EMBA logs directory\n"
fi

echo -e "[*] Checking for Docker installation"
if command -v docker >/dev/null 2>&1; then
  echo -e "[✓] Docker found, cleaning up"
  echo -e "[*] Pruning Docker system"
  if docker system prune -af; then
    echo -e "[✓] Docker system cleaned"
  else
    echo -e "[!!] Warning: Could not prune Docker system"
  fi

  echo -e "[*] Removing Docker-related packages"
  if apt-get autoremove --purge -y libnotify-bin; then
    echo -e "[✓] libnotify-bin removed"
  else
    echo -e "[!!] Warning: Could not remove libnotify-bin"
  fi

  if apt-get autoremove --purge -y inotify-tools; then
    echo -e "[✓] inotify-tools removed"
  else
    echo -e "[!!] Warning: Could not remove inotify-tools"
  fi

  if apt-get autoremove --purge -y p7zip-full; then
    echo -e "[✓] p7zip-full removed"
  else
    echo -e "[!!] Warning: Could not remove p7zip-full"
  fi

  if apt-get autoremove --purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
    echo -e "[✓] Docker packages removed\n"
  else
    echo -e "[!!] Warning: Could not remove Docker packages\n"
  fi
else
  echo -e "[*] Docker not found, skipping Docker cleanup\n"
fi

echo -e "[*] Removing EMBA package directory"
if rm -rf "${EMBAPACKAGEPATH}"; then
  echo -e "[✓] EMBA package directory removed\n"
else
  echo -e "[!!] Warning: Could not remove EMBA package directory\n"
fi

echo -e "[*] Restoring APT sources"
if sed -i 's|^# deb http|deb http|' /etc/apt/sources.list; then
  echo -e "[✓] HTTP sources restored"
else
  echo -e "[!!] Warning: Could not restore HTTP sources"
fi

if sed -i 's|^# deb https|deb https|' /etc/apt/sources.list; then
  echo -e "[✓] HTTPS sources restored"
else
  echo -e "[!!] Warning: Could not restore HTTPS sources"
fi

echo -e "[*] Removing EMBA package source from APT sources list"
if grep -v "${EMBAPACKAGEPATH}" /etc/apt/sources.list > "${INSTALLPATH}/temp"; then
  if mv "${INSTALLPATH}/temp" /etc/apt/sources.list; then
    echo -e "[✓] EMBA package source removed\n"
  else
    echo -e "[!!] Warning: Could not move temporary file back to sources.list\n"
  fi
else
  echo -e "[!!] Warning: Could not filter APT sources list\n"
fi

echo -e "[✓] EMBA uninstallation completed successfully\n"
