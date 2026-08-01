#!/usr/bin/env bash
# sync_cassandra creates any column families missing from the models — safe to
# re-run on every container start (it doesn't touch tables that already exist).
set -e

echo "[entrypoint] running sync_cassandra..."
python manage.py sync_cassandra

# worker (docker-compose.yml) shares this same entrypoint but runs rqworker —
# only seed from the web server container, and only once (seed_demo_data
# itself is idempotent, but no need to pay the query cost twice per start).
if [[ "$*" == *"runserver"* ]]; then
  echo "[entrypoint] seeding demo data (testspace@gmail.com / testconsumer@gmail.com)..."
  python manage.py seed_demo_data
fi

exec "$@"
