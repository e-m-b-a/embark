#!/bin/bash

# EMBArk - The firmware security scanning environment
#
# Copyright 2025 The AMOS Projects
# Copyright 2025-2026 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): ClProsser, SirGankalot
# Contributor(s): Benedikt Kuehne

################################################################################
# DESCRIPTION:
# This script prepares external security data (NVD and EPSS) for distribution.
# It:
#   1. Validates the script is run as root
#   2. Checks out specified versions of NVD and EPSS data repositories
#   3. Captures git metadata for version tracking
#   4. Creates a (compressed) TAR archive containing all external data
#
# USAGE:
#   ./external_host.sh <output_dir> <zip_output_path> <versions> <emba_external_dir>
#
# PARAMETERS:
#   $1 - Output directory for extracted data
#   $2 - Path where the final ZIP archive will be saved
#   $3 - Version string (comma-separated: NVD_version,EPSS_version) ref: embark.helper.get_emba_version()
#   $4 - Path to EMBA's external directory
################################################################################

set -e
cd "$(dirname "${0}")"

# Ensure script runs with root privileges (required for file operations)
if [[ "${EUID}" -ne 0 ]]; then
	echo -e "\n[!!] ERROR: This script has to be run as root\n"
	exit 1
fi

echo -e "\n[+] Starting external data preparation script"
echo -e "[*] Output Directory: ${1}"
echo -e "[*] ZIP Output Path: ${2}"
echo -e "[*] Version: ${3}"
echo -e "[*] EMBAs External-Dir Path : ${4}\n"

# Assign command-line arguments to named variables for clarity
FILEPATH="${1}"
ZIPPATH="${2}"
VERSION="${3}"
EXTERNALPATH="${4}"

# Parse comma-separated version string to extract NVD and EPSS versions
NVD_VERSION="$(echo "${VERSION}" | cut -d \, -f 1)"
EPSS_VERSION="$(echo "${VERSION}" | cut -d \, -f 2)"

echo -e "[*] File path: ${FILEPATH}"
echo -e "[*] ZIP path: ${ZIPPATH}"
echo -e "[*] External path: ${EXTERNALPATH}"
echo -e "[*] NVD version: ${NVD_VERSION}"
echo -e "[*] EPSS version: ${EPSS_VERSION}\n"

# CLEANUP PHASE: Remove any previous external data files to ensure a clean state
echo -e "[*] Cleaning up previous external data files"

# Remove old output directory (may contain incomplete/stale data)
if rm -rf "${FILEPATH}" ; then
	echo -e "[✓] Removed old directory"
else
	echo -e "[!!] Warning: Could not remove old directory"
fi

# Remove old archive (may be incomplete or from previous run)
if rm -f "${ZIPPATH}" ; then
	echo -e "[✓] Removed old archive"
else
	echo -e "[!!] Warning: Could not remove old ZIP file"
fi

# Create fresh output directory for new data
if mkdir -p "${FILEPATH}" ; then
	echo -e "[✓] Created output directory\n"
else
	echo -e "[!!] ERROR: Failed to create output directory"
	exit 1
fi

# PREPARATION PHASE: Copy installer script that will be used to extract/install the data
echo -e "[*] Copying installer script"
if cp "external_installer.sh" "${FILEPATH}/installer.sh" ; then
	echo -e "[✓] Installer script copied\n"
else
	echo -e "[!!] ERROR: Failed to copy installer script"
	exit 1
fi

# DATA VALIDATION: Ensure EMBA external directory exists before proceeding
echo -e "[*] Creating external data directory"
if ! [ -d "${EXTERNALPATH}" ]; then
	echo -e "[!!] ERROR: EMBA not installed correctly (external dir missing)\n"
	exit 1
fi

# NVD DATA CHECKOUT: Check out the specified NVD database version
# TODO: Instead of cloning, use EMBA_ROOT to copy data from there, preserving git metadata
echo -e "[*] Checking out NVD version: ${NVD_VERSION}"

# If "latest" is specified, checkout the main branch; otherwise checkout the specific version tag/branch
if [[ "${NVD_VERSION}" == "latest" ]]; then
	if git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout main; then
		echo -e "[✓] Checked out main branch"
	else
		echo -e "[!!] ERROR: Failed to checkout main branch"
		exit 1
	fi
else
	# Checkout specific version (tag or branch)
	if git -C "${EXTERNALPATH}/nvd-json-data-feeds" checkout "${NVD_VERSION}"; then
		echo -e "[✓] Checked out version ${NVD_VERSION}"
	else
		echo -e "[!!] ERROR: Failed to checkout version ${NVD_VERSION}"
		exit 1
	fi
fi

# Capture NVD git metadata (commit hash and timestamp) for version tracking
echo -e "[*] Saving NVD git metadata"
if git -C "${EXTERNALPATH}/nvd-json-data-feeds" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/nvd-json-data-feeds/git-head-meta" ; then
	echo -e "[✓] Metadata saved"
else
	echo -e "[!!] ERROR: Failed to save metadata"
	exit 1
fi

# EPSS DATA CHECKOUT: Check out the specified EPSS (Exploit Prediction Scoring System) version
echo -e "[*] Checking out EPSS version: ${EPSS_VERSION}"

# If "latest" is specified, checkout the main branch; otherwise checkout the specific version tag/branch
if [[ "${EPSS_VERSION}" == "latest" ]]; then
	if git -C "${EXTERNALPATH}/EPSS-data" checkout main; then
		echo -e "[✓] Checked out main branch"
	else
		echo -e "[!!] ERROR: Failed to checkout main branch"
		exit 1
	fi
else
	# Checkout specific version (tag or branch)
	if git -C "${EXTERNALPATH}/EPSS-data" checkout "${EPSS_VERSION}"; then
		echo -e "[✓] Checked out version ${EPSS_VERSION}"
	else
		echo -e "[!!] ERROR: Failed to checkout version ${EPSS_VERSION}"
		exit 1
	fi
fi

# Capture EPSS git metadata (commit hash and timestamp) for version tracking
echo -e "[*] Saving EPSS git metadata"
if git -C "${EXTERNALPATH}/EPSS-data" show --no-patch --format="%H %ai" HEAD > "${EXTERNALPATH}/EPSS-data/git-head-meta" ; then
	echo -e "[✓] Metadata saved"
else
	echo -e "[!!] ERROR: Failed to save metadata"
	exit 1
fi


# COMPRESSION PHASE: Create a compressed TAR archive containing all external data
# This archive will be distributed for installation on other systems
echo -e "[*] Creating compressed archive at: ${ZIPPATH}"

# Create gzip-compressed TAR archive (from ~2.9 GiB to compressed size)
if tar --update -f "${ZIPPATH}" "${FILEPATH}" ; then	# skip compression for comp speed
# Alternative: if tar -czf "${ZIPPATH}" "${EXTERNALPATH}" ; then	# compress too
	echo -e "[✓] Archive created successfully\n"
else
	echo -e "[!!] ERROR: Failed to create archive"
	exit 1
fi

echo -e "[✓] External data preparation completed successfully\n"
