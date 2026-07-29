"""
Dump toàn bộ schema (columns + types + keys) của tất cả table trong keyspace.
"""
import os
import sys

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

DB_HOST = "127.0.0.1"
DB_PORT = 9042
DB_USER = "cassandra"
DB_PASS = "cassandra"
DB_NAME = "lms_keyspace"

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DB_"):
                k, _, v = line.partition("=")
                v = v.strip()
                if k == "DB_HOST": DB_HOST = v
                elif k == "DB_PORT": DB_PORT = int(v)
                elif k == "DB_USERNAME": DB_USER = v
                elif k == "DB_PASSWORD": DB_PASS = v
                elif k == "DB_DATABASE": DB_NAME = v

print(f"Connecting to {DB_HOST}:{DB_PORT} keyspace={DB_NAME}")
auth = PlainTextAuthProvider(DB_USER, DB_PASS) if DB_USER else None
cluster = Cluster([DB_HOST], port=DB_PORT, auth_provider=auth, protocol_version=4)
session = cluster.connect(DB_NAME)

tables = list(session.execute(
    "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s ORDER BY table_name",
    [DB_NAME]
))

print(f"Found {len(tables)} tables\n")
print("=" * 100)

for t in tables:
    tbl = t.table_name
    print(f"\n▸ {tbl}")
    print("-" * 100)

    cols = list(session.execute(
        "SELECT column_name, type, kind, position FROM system_schema.columns "
        "WHERE keyspace_name = %s AND table_name = %s",
        [DB_NAME, tbl]
    ))

    # Lấy partition key + clustering columns
    pk_rows = [c for c in cols if c.kind in ('partition_key', 'clustering')]
    pk_rows.sort(key=lambda r: (0 if r.kind == 'partition_key' else 1, r.position))
    pk_rows.sort(key=lambda r: (0 if r.kind == 'partition_key' else 1, r.position))
    pk_info = ", ".join(f"{r.column_name} ({r.kind})" for r in pk_rows)

    # Indexes
    idx_rows = list(session.execute(
        "SELECT index_name, options FROM system_schema.indexes "
        "WHERE keyspace_name = %s AND table_name = %s",
        [DB_NAME, tbl]
    ))
    idx_info = ", ".join(r.index_name for r in idx_rows) if idx_rows else "(none)"

    print(f"  PK: {pk_info}")
    print(f"  Indexes: {idx_info}")

    for c in cols:
        marker = {
            'partition_key': 'PK',
            'clustering':   'CK',
            'regular':      '  ',
            'static':       'ST',
        }.get(c.kind, '  ')
        print(f"  [{marker}] {c.column_name:32s} {c.type}")

print("\n" + "=" * 100)
print(f"TOTAL: {len(tables)} tables")
cluster.shutdown()
