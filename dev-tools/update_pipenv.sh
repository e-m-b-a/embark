#!/bin/bash
# EMBArk - The firmware security scanning environment
#
# Copyright 2024 Siemens Energy AG
#
# EMBArk comes with ABSOLUTELY NO WARRANTY.
#
# EMBArk is licensed under MIT
#
# Author(s): Benedikt Kuehne

# Description: Automates updating the pipfile

# 1. find out which installation
INSTALL=""

INSTALL="deploy"

if grep -q "EMBARK_INSTALL=dev" ./.env ; then
  INSTALL="dev"
fi

# 2. update pipfile
if [[ "${INSTALL}" == "dev" ]]; then
  MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 pipenv update --dev -v
else
  echo "This is not a developer setup...still trying to update"
  MYSQLCLIENT_LDFLAGS='-L/usr/mysql/lib -lmysqlclient -lssl -lcrypto -lresolv' MYSQLCLIENT_CFLAGS='-I/usr/include/mysql/' PIPENV_VENV_IN_PROJECT=1 pipenv update
fi
# push to web-dir if available