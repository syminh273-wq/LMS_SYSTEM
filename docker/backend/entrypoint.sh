#!/usr/bin/env bash
# sync_cassandra creates any column families missing from the models — safe to
# re-run on every container start (it doesn't touch tables that already exist).
set -e

echo "[entrypoint] running sync_cassandra..."
python manage.py sync_cassandra

exec "$@"
