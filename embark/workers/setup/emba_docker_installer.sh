#!/bin/bash

set -e
cd "$(dirname "$0")"

if [[ ${EUID} -ne 0 ]]; then
	echo "This script has to be run as root"
	exit 1
fi

FILEPATH="."

# Reset
systemctl is-active --quiet docker || systemctl start docker
docker system prune -af

# Load EMBA image
docker image load -i "${FILEPATH}/emba-docker-image.tar"
