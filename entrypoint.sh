#!/bin/sh
set -e

echo "Installing dependencies..."
if [ -n "$PIP_PROXY" ]; then
    pip install --proxy="$PIP_PROXY" -r /web/medtracker/requirements.txt
else
    pip install -r /web/medtracker/requirements.txt
fi

echo "Migrations..."
python manage.py migrate --noinput
python manage.py migrate --database=logs --noinput

echo "Migrations success"
exec "$@"