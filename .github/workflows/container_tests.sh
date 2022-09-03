#!/bin/bash
set -x

/usr/local/share/docker-init.sh

cd /project
source /venv/bin/activate

touch requirements_dev.txt
pip install -r requirements_dev.txt -e .[dev]
pip freeze --exclude-editable > dist/requirements_dev.txt

pipdeptree

pytest tests
