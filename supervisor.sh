#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2020 - 2025 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Supervisor for EMBArk server

LOG_FILE='/var/log/embark-supervisor.log'

# Close standard output file descriptors and reroute to log
exec 1<&-
exec 2<&-
exec 1<>${LOG_FILE}
exec 2>&1

while :; do
  if ! ip a show embark_backend | grep -q "172.22.0.1" ; then
    systemctl restart docker
    echo "$(date +"%D %T")"" restarted docker"
  fi
  sleep 2s
done
