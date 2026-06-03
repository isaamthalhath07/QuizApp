#!/bin/bash
set -euo pipefail

python3 -m pip install --break-system-packages -r requirements.txt

cd quiz_app
python3 manage.py collectstatic --noinput --clear

cd ..
mkdir -p staticfiles_build
cp -r quiz_app/staticfiles staticfiles_build/static
