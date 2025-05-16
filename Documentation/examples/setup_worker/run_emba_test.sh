#!/bin/bash

if [[ $EUID -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FIRMWARE_PATH="$(realpath ./firmware.zip)"
EMBA_PATH="/root/emba"

cd "${EMBA_PATH}"

sudo DISABLE_STATUS_BAR=1 DISABLE_NOTIFICATIONS=1 HTML=1 FORMAT_LOG=1 ./emba -f "${FIRMWARE_PATH}" -l ./emba_logs -p "./scan-profiles/default-scan-no-notify.emba" -Z "" -Y ""
