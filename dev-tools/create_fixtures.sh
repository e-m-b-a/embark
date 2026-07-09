#!/bin/bash
# Script to create fixture files for Django models
# Usage: ./create_fixtures.sh
# Note: server must be running and the database must be populated with the necessary data before running this script.
cd "$(dirname "${0}")" || exit 1
cd .. || exit 1

# shellcheck disable=SC1091
source ./.venv/bin/activate || exit 1

cd embark || exit 1
# python manage.py dumpdata auth.group > ./users/fixtures/default_groups.json
python manage.py dumpdata django_celery_beat > ./updater/fixtures/default_tasks.json