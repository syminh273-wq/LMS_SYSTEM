#!/usr/bin/env bash
# Wraps the official Scylla entrypoint: starts Scylla normally, then waits for
# CQL to accept authenticated connections and creates the app keyspace once.
# Scylla itself keeps running even if keyspace creation fails/times out.
set -uo pipefail

/docker-entrypoint.py "$@" &
SCYLLA_PID=$!

CQL_USER="${CASSANDRA_USER:-cassandra}"
CQL_PASSWORD="${CASSANDRA_PASSWORD:-cassandra}"
KEYSPACE="${CASSANDRA_KEYSPACE:-lms_keyspace}"

# Scylla's docker-entrypoint auto-binds CQL to the container's own IP
# (--rpc-address), not to loopback — 127.0.0.1:9042 refuses connections
# from inside this same container, so resolve our own address instead.
SELF_IP="$(hostname -i)"

echo "[init] waiting for Scylla CQL ($SELF_IP:9042) to accept authenticated connections..."
attempt=0
until cqlsh -u "$CQL_USER" -p "$CQL_PASSWORD" -e "SELECT release_version FROM system.local" "$SELF_IP" 9042 >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "[init] gave up waiting after $((attempt * 2))s — Scylla is still running, create '$KEYSPACE' manually." >&2
    wait "$SCYLLA_PID"
    exit $?
  fi
  sleep 2
done

echo "[init] creating keyspace '$KEYSPACE' if not exists..."
cqlsh -u "$CQL_USER" -p "$CQL_PASSWORD" -e \
  "CREATE KEYSPACE IF NOT EXISTS $KEYSPACE WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};" \
  "$SELF_IP" 9042 \
  && echo "[init] keyspace '$KEYSPACE' ready." \
  || echo "[init] failed to create keyspace '$KEYSPACE' — check logs above." >&2

wait "$SCYLLA_PID"
