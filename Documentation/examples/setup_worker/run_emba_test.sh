#!/bin/bash

cd "/root/emba"

FIRMWARE_PATH="./firmware.zip"

sudo DISABLE_STATUS_BAR=1 DISABLE_NOTIFICATIONS=1 HTML=1 FORMAT_LOG=1 ./emba -f "${FIRMWARE_PATH}" -l ./emba_logs -p ./scan-profiles/default-scan-no-notify.emba  -Z "" -Y ""
