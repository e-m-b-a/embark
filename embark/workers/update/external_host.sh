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
# Contributor(s): Benedikt Kuehne

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting external data preparation script"
echo -e "[*] Output Directory: $1"
echo -e "[*] ZIP Output Path: $2"
echo -e "[*] Version: $3\n"

FILEPATH="$1"
ZIPPATH="$2"
VERSION="$3"
EXTERNALPATH="${FILEPATH}/external"

NVD_VERSION=$(echo "${VERSION}" | cut -d \, -f 1)
EPSS_VERSION=$(echo "${VERSION}" | cut -d \, -f 2)

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] ZIP path: ${ZIPPATH}"
echo -e "[*] External path: ${EXTERNALPATH}"
echo -e "[*] NVD version: ${NVD_VERSION}"
echo -e "[*] EPSS version: ${EPSS_VERSION}\n"

### Reset
echo -e "[*] Cleaning up previous external data files"
if rm -rf "${FILEPATH}" ; then
	echo -e "[✓] Removed old directory"
else
	echo -e "[!!] Warning: Could not remove old directory"
fi
if rm -f "${ZIPPATH}" ; then
	echo -e "[✓] Removed old ZIP file"
else
	echo -e "[!!] Warning: Could not remove old ZIP file"
fi
if mkdir -p "${FILEPATH}" ; then
	echo -e "[✓] Created output directory\n"
else
	echo -e "[!!] ERROR: Failed to create output directory"
	exit 1
fi

### Copy scripts
echo -e "[*] Copying installer script"
if cp "external_installer.sh" "${FILEPATH}/installer.sh" ; then
	echo -e "[✓] Installer script copied\n"
else
	echo -e "[!!] ERROR: Failed to copy installer script"
	exit 1
fi

### Download external data
echo -e "[*] Creating external data directory"
if mkdir -p "${EXTERNALPATH}" ; then
	echo -e "[✓] Directory created\n"
else
	echo -e "[!!] ERROR: Failed to create directory"
	exit 1
fi

echo -e "[*] Cloning NVD JSON data feeds repository"
if git clone https://github.com/EMBA-support-repos/nvd-json-data-feeds.git "${EXTERNALPATH}/nvd-json-data-feeds" ; then
	echo -e "[✓] Repository cloned"
else
	echo -e "[!!] ERROR: Failed to clone NVD repository"
	exit 1
fi
echo -e "[*] Checking out NVD version: ${NVD_VERSION}"
if [[ "${NVD_VERSION}" == "latest" ]]; then
	git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout main
	if [ $? -eq 0 ] ; then
		echo -e "[✓] Checked out main branch"
	else
		echo -e "[!!] ERROR: Failed to checkout main branch"
		exit 1
	fi
else
	git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout "${NVD_VERSION}"
	if [ $? -eq 0 ] ; then
		echo -e "[✓] Checked out version ${NVD_VERSION}"
	else
		echo -e "[!!] ERROR: Failed to checkout version ${NVD_VERSION}"
		exit 1
	fi
fi
echo -e "[*] Saving NVD git metadata"
if git -C "${EXTERNALPATH}/nvd-json-data-feeds" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/nvd-json-data-feeds/git-head-meta" ; then
	echo -e "[✓] Metadata saved"
else
	echo -e "[!!] ERROR: Failed to save metadata"
	exit 1
fi
echo -e "[*] Removing NVD git directory"
if rm -rf "${EXTERNALPATH}/nvd-json-data-feeds/.git" ; then
	echo -e "[✓] Git directory removed\n"
else
	echo -e "[!!] Warning: Could not remove git directory\n"
fi

echo -e "[*] Cloning EPSS data repository"
if git clone https://github.com/EMBA-support-repos/EPSS-data.git "${EXTERNALPATH}/EPSS-data" ; then
	echo -e "[✓] Repository cloned"
else
	echo -e "[!!] ERROR: Failed to clone EPSS repository"
	exit 1
fi
echo -e "[*] Checking out EPSS version: ${EPSS_VERSION}"
if [[ "${EPSS_VERSION}" == "latest" ]]; then
	git -C "${EXTERNALPATH}/EPSS-data" checkout main
	if [ $? -eq 0 ] ; then
		echo -e "[✓] Checked out main branch"
	else
		echo -e "[!!] ERROR: Failed to checkout main branch"
		exit 1
	fi
else
	git -C "${EXTERNALPATH}/EPSS-data" checkout "${EPSS_VERSION}"
	if [ $? -eq 0 ] ; then
		echo -e "[✓] Checked out version ${EPSS_VERSION}"
	else
		echo -e "[!!] ERROR: Failed to checkout version ${EPSS_VERSION}"
		exit 1
	fi
fi
echo -e "[*] Saving EPSS git metadata"
if git -C "${EXTERNALPATH}/EPSS-data" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/EPSS-data/git-head-meta" ; then
	echo -e "[✓] Metadata saved"
else
	echo -e "[!!] ERROR: Failed to save metadata"
	exit 1
fi
echo -e "[*] Removing EPSS git directory"
if rm -rf "${EXTERNALPATH}/EPSS-data/.git" ; then
	echo -e "[✓] Git directory removed\n"
else
	echo -e "[!!] Warning: Could not remove git directory\n"
fi

### Fake venv (packages are broken)
echo -e "[*] Creating fake Python virtual environment structure"
if mkdir -p "${EXTERNALPATH}/emba_venv/bin" ; then
	echo -e "[✓] venv directories created"
else
	echo -e "[!!] ERROR: Failed to create venv directories"
	exit 1
fi
if touch "${EXTERNALPATH}/emba_venv/bin/activate" ; then
	echo -e "[✓] Activation script created\n"
else
	echo -e "[!!] ERROR: Failed to create activation script"
	exit 1
fi

echo -e "[*] Creating compressed archive at: ${ZIPPATH}"
if tar czf "${ZIPPATH}" -C "${FILEPATH}" . ; then
	echo -e "[✓] Archive created successfully\n"
else
	echo -e "[!!] ERROR: Failed to create archive"
	exit 1
fi

echo -e "[✓] External data preparation completed successfully\n"
