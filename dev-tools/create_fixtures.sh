#!/bin/bash
# Script to create fixture files for Django models
# Usage: ./create_fixtures.sh
cd "$(dirname "${0}")" || exit 1
cd .. || exit 1

# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

cd embark || exit 1
python manage.py dumpdata auth.group > ./users/fixtures/default_groups.json