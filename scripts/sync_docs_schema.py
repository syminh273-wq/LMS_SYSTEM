"""Standalone Cassandra schema sync.

Bypasses Django's INSTALLED_APPS URL chain (which is currently broken on
this branch due to an unrelated langchain import error in
core.ai.langchain.agent). Only syncs the models we need.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
django.setup()

from django.conf import settings
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import AddressTranslator
from features.resource.models.resource_folder import ResourceFolder
from features.resource.models.resource import Resource


class _CT(AddressTranslator):
    def __init__(self, contact_point):
        self._cp = contact_point
    def translate(self, addr):
        return self._cp


def main():
    db = settings.DATABASES['default']
    keyspace = db['NAME']
    host = db['HOST']
    user = db['USER']
    password = db['PASSWORD']
    print(f"Connecting to Cassandra: {host} keyspace={keyspace} user={user}")

    cluster = Cluster(
        [host],
        port=int(db['PORT']),
        auth_provider=PlainTextAuthProvider(username=user, password=password),
        address_translator=_CT(host),
    )
    session = cluster.connect(keyspace)

    # 1) Create resource_folders table
    print(f"Creating table resource_folders...")
    session.execute("""
        CREATE TABLE IF NOT EXISTS resource_folders (
            classroom_id uuid,
            uid uuid,
            name text,
            parent_folder_id uuid,
            owner_id uuid,
            order_index int,
            color text,
            created_at timestamp,
            updated_at timestamp,
            is_deleted boolean,
            deleted_at timestamp,
            PRIMARY KEY (classroom_id, uid)
        ) WITH CLUSTERING ORDER BY (uid DESC)
    """)
    print("  OK")

    # classroom_id is the partition key, so it's already indexable via PK.
    # owner_id is non-key, useful for "my folders" queries.
    print("Creating secondary index on resource_folders.owner_id ...")
    session.execute("CREATE INDEX IF NOT EXISTS resource_folders_owner_id_idx ON resource_folders (owner_id)")
    print("  OK")

    # 2) Add new columns to resource_resources
    print("Altering resource_resources to add folder_id, order_index ...")
    for col, ctype in [("folder_id", "uuid"), ("order_index", "int")]:
        try:
            session.execute(f"ALTER TABLE resource_resources ADD {col} {ctype}")
            print(f"  + {col} ({ctype})")
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" in msg or "invalid column" in msg or "duplicate" in msg:
                print(f"  = {col} already exists")
            else:
                print(f"  ! {col}: {exc}")
                raise

    # 3) Create resource_doc_reading_progress
    print("Creating table resource_doc_reading_progress ...")
    session.execute("""
        CREATE TABLE IF NOT EXISTS resource_doc_reading_progress (
            classroom_id uuid,
            student_id uuid,
            resource_uid uuid,
            read_progress int,
            is_completed boolean,
            completed_at timestamp,
            last_opened_at timestamp,
            created_at timestamp,
            updated_at timestamp,
            is_deleted boolean,
            deleted_at timestamp,
            PRIMARY KEY (classroom_id, student_id, resource_uid)
        ) WITH CLUSTERING ORDER BY (student_id DESC, resource_uid DESC)
    """)
    print("  OK")

    # 4) Create resource_doc_notes
    print("Creating table resource_doc_notes ...")
    session.execute("""
        CREATE TABLE IF NOT EXISTS resource_doc_notes (
            resource_uid uuid,
            uid uuid,
            classroom_id uuid,
            student_id uuid,
            content text,
            page int,
            x_pct float,
            y_pct float,
            progress_at float,
            color text,
            created_at timestamp,
            updated_at timestamp,
            is_deleted boolean,
            deleted_at timestamp,
            PRIMARY KEY (resource_uid, uid)
        ) WITH CLUSTERING ORDER BY (uid DESC)
    """)
    print("  OK")

    print("Creating secondary index on resource_doc_notes.student_id ...")
    session.execute("CREATE INDEX IF NOT EXISTS resource_doc_notes_student_id_idx ON resource_doc_notes (student_id)")
    print("  OK")
    print("Creating secondary index on resource_doc_notes.classroom_id ...")
    session.execute("CREATE INDEX IF NOT EXISTS resource_doc_notes_classroom_id_idx ON resource_doc_notes (classroom_id)")
    print("  OK")

    print("Done.")
    cluster.shutdown()


if __name__ == '__main__':
    main()
