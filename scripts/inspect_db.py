"""
Deep DB inspection script — verifies why certificate isn't being issued.

Usage:
    cd /Users/siminh/PycharmProjects/LMS_BACKEND
    source .venv/bin/activate
    python inspect_db.py
"""

import os
import sys
from uuid import UUID

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.configs.django')

import django
try:
    django.setup()
except Exception as e:
    print(f"[!] Django setup failed: {e}")
    print("    Trying alternative settings module…")

# The collection UID from the log
COLLECTION_UID = "019f6b51-5c51-7f02-9ff4-47c8f6755dce"
CLASSROOM_UID = "019f6b51-cf9b-7ced-8c50-9ff618950802"
QUIZ_UIDS = [
    "019f6b50-f0d5-7ba7-9dd6-1c8e89c1e2de",
    "019f6b50-6fa6-70f0-af8f-167f504fbff6",
]

print("=" * 80)
print(f"INSPECTING DB FOR OOP CERTIFICATE FLOW")
print("=" * 80)
print(f"Collection: {COLLECTION_UID}")
print(f"Classroom:  {CLASSROOM_UID}")
print(f"Quizzes:    {QUIZ_UIDS}")
print()

# Try to import models directly using cqlengine (no Django app loading required)
try:
    from cassandra.cqlengine import connection
    from cassandra.cqlengine.management import sync_table
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
except ImportError as e:
    print(f"[!] cassandra driver not installed: {e}")
    sys.exit(1)

# Try reading .env manually
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

print(f"[*] Connecting to Cassandra at {DB_HOST}:{DB_PORT}, keyspace={DB_NAME}")

try:
    auth = PlainTextAuthProvider(DB_USER, DB_PASS) if DB_USER else None
    cluster = Cluster([DB_HOST], port=DB_PORT, auth_provider=auth, protocol_version=4)
    session = cluster.connect(DB_NAME)
    print(f"[+] Connected.\n")
except Exception as e:
    print(f"[!] Connection failed: {e}")
    print("    Make sure Cassandra/ScyllaDB is running on {DB_HOST}:{DB_PORT}")
    sys.exit(1)

def query_one(sql, params=None):
    try:
        stmt = session.prepare(sql)
        rows = list(session.execute(stmt, params or []))
        return rows
    except Exception as e:
        print(f"[!] Query failed: {e}")
        return []

def query_all(sql, params=None, limit=100):
    try:
        rows = list(session.execute(sql, params or []))
        return rows[:limit]
    except Exception as e:
        print(f"[!] Query failed: {e}")
        return []

def hr(title):
    print()
    print("─" * 80)
    print(f"  {title}")
    print("─" * 80)

# ── 1. List all keyspace tables ──
hr("STEP 1 — Keyspace tables")
tables = query_all("SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s", [DB_NAME])
for r in tables:
    print(f"  • {r.table_name}")

# ── 2. Find IssuedCertificate schema (find correct table name) ──
hr("STEP 2 — Finding certificate / log tables")
cert_tables = [r.table_name for r in tables if 'cert' in r.table_name.lower()]
log_tables = [r.table_name for r in tables if 'log' in r.table_name.lower()]
coll_tables = [r.table_name for r in tables if 'collect' in r.table_name.lower() or 'collection' in r.table_name.lower()]
member_tables = [r.table_name for r in tables if 'member' in r.table_name.lower()]

print(f"Certificate tables: {cert_tables}")
print(f"Quiz log tables:    {log_tables}")
print(f"Collection tables:  {coll_tables}")
print(f"Member tables:      {member_tables}")

# ── 3. Look at the QuizCollection row for the OOP collection ──
hr(f"STEP 3 — QuizCollection row (uid={COLLECTION_UID})")
if coll_tables:
    for tbl in coll_tables:
        rows = query_all(f"SELECT * FROM {tbl} WHERE uid = %s", [UUID(COLLECTION_UID)])
        if rows:
            for r in rows:
                print(f"  Table: {tbl}")
                for col in r._fields:
                    val = getattr(r, col)
                    if col == 'certificate_id' and val:
                        val_str = f"{val} ← ★ CERT TEMPLATE LINKED"
                    elif col == 'certificate_id' and not val:
                        val_str = "null ← ✗ NO CERT TEMPLATE LINKED (THIS IS THE BUG!)"
                    else:
                        val_str = str(val)
                    print(f"    {col:30s} = {val_str}")
            break
    else:
        print(f"  [!] Collection {COLLECTION_UID} NOT FOUND in any of: {coll_tables}")
else:
    print("  [!] No collection tables found")

# ── 4. Look at IssuedCertificate rows ──
hr("STEP 4 — IssuedCertificate rows for this collection")
if cert_tables:
    for tbl in cert_tables:
        # Try with collection_id filter
        try:
            rows = query_all(f"SELECT * FROM {tbl} WHERE collection_id = %s ALLOW FILTERING", [UUID(COLLECTION_UID)])
            if rows:
                print(f"  Found {len(rows)} row(s) in {tbl}:")
                for r in rows:
                    for col in r._fields:
                        val = getattr(r, col)
                        print(f"    {col:30s} = {val}")
            else:
                print(f"  No rows in {tbl} for collection_id={COLLECTION_UID}")
        except Exception as e:
            print(f"  Could not query {tbl}: {e}")

# ── 5. Look at QuizLog rows for the OOP quizzes ──
hr("STEP 5 — QuizLog rows for OOP quizzes (best score per quiz)")
if log_tables:
    for qz_uid in QUIZ_UIDS:
        print(f"\n  Quiz: {qz_uid}")
        for tbl in log_tables:
            try:
                rows = query_all(
                    f"SELECT * FROM {tbl} WHERE quiz_id = %s AND classroom_id = %s ALLOW FILTERING",
                    [UUID(qz_uid), UUID(CLASSROOM_UID)]
                )
                if rows:
                    print(f"    Found {len(rows)} row(s) in {tbl}:")
                    best_pct = -1
                    best_row = None
                    for r in rows:
                        pct = getattr(r, 'score_pct', None) or 0
                        if pct > best_pct:
                            best_pct = pct
                            best_row = r
                        for col in ['score_pct', 'score', 'attempt_number', 'student_id', 'submitted_at']:
                            if hasattr(r, col):
                                print(f"      {col:20s} = {getattr(r, col)}")
                    if best_row:
                        print(f"    ★ Best score_pct: {best_pct}")
            except Exception as e:
                print(f"    Could not query {tbl}: {e}")

# ── 6. Look at QuizCollectionItem rows (the missions in this collection) ──
hr("STEP 6 — QuizCollectionItem rows (missions in OOP collection)")
item_tables = [r.table_name for r in tables if 'item' in r.table_name.lower() or 'collection_item' in r.table_name.lower()]
if item_tables:
    for tbl in item_tables:
        try:
            rows = query_all(f"SELECT * FROM {tbl} WHERE collection_id = %s ALLOW FILTERING", [UUID(COLLECTION_UID)])
            if rows:
                print(f"  Found {len(rows)} mission(s) in {tbl}:")
                for r in rows:
                    for col in r._fields:
                        print(f"    {col:30s} = {getattr(r, col)}")
                    print()
        except Exception as e:
            print(f"  Could not query {tbl}: {e}")

# ── 7. Look at QuizCollectionAssignment (is collection assigned to classroom?) ──
hr("STEP 7 — QuizCollectionAssignment row (collection ↔ classroom link)")
assign_tables = [r.table_name for r in tables if 'assign' in r.table_name.lower()]
if assign_tables:
    for tbl in assign_tables:
        try:
            rows = query_all(
                f"SELECT * FROM {tbl} WHERE collection_id = %s AND classroom_id = %s ALLOW FILTERING",
                [UUID(COLLECTION_UID), UUID(CLASSROOM_UID)]
            )
            if rows:
                print(f"  Found {len(rows)} assignment(s) in {tbl}:")
                for r in rows:
                    for col in r._fields:
                        print(f"    {col:30s} = {getattr(r, col)}")
            else:
                print(f"  ✗ NO assignment found — collection is NOT linked to this classroom!")
        except Exception as e:
            print(f"  Could not query {tbl}: {e}")

# ── 8. Find the student UID by listing members of the classroom ──
hr("STEP 8 — Members of classroom 019f6b51-cf9b-7ced-8c50-9ff618950802")
if member_tables:
    for tbl in member_tables:
        try:
            rows = query_all(
                f"SELECT * FROM {tbl} WHERE classroom_uid = %s ALLOW FILTERING",
                [UUID(CLASSROOM_UID)]
            )
            if rows:
                print(f"  Found {len(rows)} member(s) in {tbl}:")
                for r in rows:
                    member_id = getattr(r, 'member_id', None)
                    role = getattr(r, 'role', None)
                    status = getattr(r, 'status', None)
                    is_del = getattr(r, 'is_deleted', None)
                    print(f"    member_id={member_id}  role={role}  status={status}  is_deleted={is_del}")
        except Exception as e:
            print(f"  Could not query {tbl}: {e}")

# ── 9. List all students (members) and check issued certs ──
hr("STEP 9 — ALL IssuedCertificate rows (any student)")
if cert_tables:
    for tbl in cert_tables:
        try:
            # Try a count first
            count_stmt = session.prepare(f"SELECT COUNT(*) FROM {tbl}")
            count = session.execute(count_stmt).one()[0]
            print(f"  Total certs in {tbl}: {count}")
            if count > 0 and count < 50:
                rows = query_all(f"SELECT * FROM {tbl} LIMIT 50")
                for r in rows:
                    print(f"    student={getattr(r, 'student_id', '?')}  collection={getattr(r, 'collection_id', '?')}  classroom={getattr(r, 'classroom_id', '?')}  issued_at={getattr(r, 'issued_at', '?')}")
        except Exception as e:
            print(f"  Could not query {tbl}: {e}")

# ── 10. Look at QuizAssignment (passing_score_pct) for the OOP quizzes ──
hr("STEP 10 — QuizAssignment passing scores for OOP quizzes")
qassign_tables = [r.table_name for r in tables if 'quiz_assign' in r.table_name.lower() or 'assignment' in r.table_name.lower()]
if qassign_tables:
    for qz_uid in QUIZ_UIDS:
        print(f"\n  Quiz: {qz_uid}")
        for tbl in qassign_tables:
            try:
                rows = query_all(
                    f"SELECT * FROM {tbl} WHERE quiz_id = %s AND classroom_id = %s ALLOW FILTERING",
                    [UUID(qz_uid), UUID(CLASSROOM_UID)]
                )
                if rows:
                    for r in rows:
                        for col in r._fields:
                            val = getattr(r, col)
                            if 'passing' in col.lower():
                                print(f"    ★ {col:30s} = {val}")
                            else:
                                print(f"      {col:30s} = {val}")
            except Exception as e:
                print(f"    Could not query {tbl}: {e}")

# ── 11. Quiz schema: look at passing_score_pct column type ──
hr("STEP 11 — Schema of quiz_assignment / quiz_log / issued_certificates (key columns)")
schema_tables = ['quiz_assignment', 'quiz_log', 'issued_certificates', 'quiz_collection', 'quiz_collection_item', 'quiz_collection_assignment']
for t in schema_tables:
    try:
        rows = query_all(
            "SELECT column_name, type, kind FROM system_schema.columns "
            "WHERE keyspace_name = %s AND table_name = %s",
            [DB_NAME, t]
        )
        if rows:
            print(f"\n  {t}:")
            for r in rows:
                marker = " ★" if r.kind == 'partition_key' else (" ◦" if r.kind == 'clustering' else "  ")
                print(f"    {marker} {r.column_name:30s} {r.type:25s} ({r.kind})")
    except Exception as e:
        pass

print()
print("=" * 80)
print("DONE")
print("=" * 80)
cluster.shutdown()
