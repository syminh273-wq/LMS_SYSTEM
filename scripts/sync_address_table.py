"""Sync the Address table to Cassandra.

Bypasses the broken `core.ai.langchain.agent` chain by syncing only the
Address model (no Django management command required).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')

import django
django.setup()

from django.db import connections
from django_cassandra_engine.models import DjangoCassandraModel
from django_cassandra_engine.utils import get_engine_from_db_alias
from cassandra.cqlengine import management
from cassandra.cqlengine.models import Model as CqlModel

from features.account.consumer.models.address import Address


def sync_model(model, alias):
    name = model.__table_name__
    try:
        management.Model = (CqlModel, DjangoCassandraModel)
        management.sync_table(
            model,
            keyspaces=[connections[alias].settings_dict['NAME']],
            connections=[alias],
        )
        print(f"[sync_address] OK   {name}")
    except Exception as exc:
        msg = str(exc)
        if 'already exists' in msg.lower():
            print(f"[sync_address] SKIP {name} (already exists)")
        else:
            print(f"[sync_address] FAIL {name}: {exc}")


if __name__ == '__main__':
    for alias in connections:
        if get_engine_from_db_alias(alias) != 'django_cassandra_engine':
            continue
        sync_model(Address, alias)
