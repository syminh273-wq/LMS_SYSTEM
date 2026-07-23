"""
Standalone script: tạo table `user_profiles` trong Cassandra mà không cần Django.
Chạy: python scripts/sync_user_profile_table.py
"""
import os
import sys
import django
from pathlib import Path

# Bootstrap Django
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
django.setup()

from cassandra.cqlengine import management
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from decouple import config
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from datetime import datetime
import uuid


# Read Cassandra config
host = config('CASSANDRA_HOST', default='127.0.0.1')
port = int(config('CASSANDRA_PORT', default='9042'))
keyspace = config('DB_DATABASE', default='lms_keyspace')
user = config('CASSANDRA_USER', default='cassandra')
pwd  = config('CASSANDRA_PASSWORD', default='cassandra')


def main():
    # 1. Ensure keyspace
    cluster = Cluster([host], port=port, auth_provider=PlainTextAuthProvider(user, pwd) if user else None)
    session = cluster.connect()
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {keyspace}
        WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': '1' }}
    """)
    print(f'[OK] keyspace={keyspace}')

    # 2. Use keyspace
    session.set_keyspace(keyspace)

    # 3. Create table directly
    session.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            bucket           int,
            owner_id         uuid,
            owner_type       text,
            avatar_url       text,
            cover_url        text,
            bio              text,
            major            text,
            department       text,
            skills           list<text>,
            github           text,
            linkedin         text,
            website          text,
            posts_count      int,
            followers_count  int,
            following_count  int,
            updated_at       timestamp,
            PRIMARY KEY (bucket, owner_id)
        )
    """)
    print('[OK] table=user_profiles created')

    # 4. Create index on owner_id for global queries
    session.execute("""
        CREATE INDEX IF NOT EXISTS user_profiles_owner_id_idx
        ON user_profiles (owner_id)
    """)
    print('[OK] index=user_profiles_owner_id_idx')

    cluster.shutdown()


if __name__ == '__main__':
    main()
