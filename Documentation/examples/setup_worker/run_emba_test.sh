#!/bin/bash

FIRMWARE_PATH="./test/firmware.zip"
EMBA_PATH="/root/emba"

sudo DISABLE_STATUS_BAR=1 DISABLE_NOTIFICATIONS=1 HTML=1 FORMAT_LOG=1 "${EMBA_PATH}/emba" -f "${FIRMWARE_PATH}" -l ./emba_logs -p "${EMBA_PATH}/scan-profiles/default-scan-no-notify.emba" -Z "" -Y ""
