#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2024-2025 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Automates writing the VERSION.txt

# create version
sed -i "s|-.*|-$(git describe --always --exclude '*')|1" "$(dirname "${0}")/../VERSION.txt"
# and tag for version
# TODO