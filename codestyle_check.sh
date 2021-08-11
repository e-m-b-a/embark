#!/bin/bash

echo -e "[*] Searching shell scripts and test with shellcheck"
shellcheck codestyle_check.sh
find embark -iname "*.sh" -exec shellcheck {} \;

echo -e "[*] Searching python files and test with pycodestyle.py"
find embark -name "*.py" -exec python3 /usr/lib/python3/dist-packages/pycodestyle.py --first {} \;

echo -e "[*] Test project with pytest"
pytest

#echo -e "[*] Searching python files and test with pylint:"
#pylint --max-line-length=240 embark/*
