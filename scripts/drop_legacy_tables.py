"""
Drop legacy tables that have been refactored / removed in Phase 1-3.

Run after `python manage.py lms_sync_cassandra` to clean up tables
that are no longer referenced by any model.
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

DROPS = [
    # Phase 1
    'resource_doc_notes',
    'resource_doc_reading_progress',
    'ranking_xp_rules',
    # Phase 2
    'course_classroom_blacklists',
    'course_teacher_global_blacklists',
    'quiz_collection_items',
    # Phase 3
    'course_courses',
    'course_lessons',
    'consumer_posts',
    'post_comments',
    'post_likes',
    'user_follows',
]


def main():
    auth = PlainTextAuthProvider(DB_USER, DB_PASS) if DB_USER else None
    cluster = Cluster([DB_HOST], port=DB_PORT, auth_provider=auth, protocol_version=4)
    session = cluster.connect(DB_NAME)

    existing = {r.table_name for r in session.execute(
        "SELECT table_name FROM system_schema.tables WHERE keyspace_name=%s", [DB_NAME]
    )}

    for t in DROPS:
        if t in existing:
            try:
                session.execute(f"DROP TABLE IF EXISTS {DB_NAME}.{t}")
                print(f"[OK]   dropped {t}")
            except Exception as e:
                print(f"[FAIL] {t}: {e}")
        else:
            print(f"[skip] {t} (not present)")

    cluster.shutdown()


if __name__ == "__main__":
    main()
