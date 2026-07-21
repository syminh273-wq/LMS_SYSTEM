"""Additive Cassandra schema sync.

Runs the same `management.sync_table` call that
`python manage.py sync_cassandra` does, but directly (without Django's
management command) to avoid importing the broken `core.ai.langchain.agent`
chain that fails on this machine.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
django.setup()

from django.db import connections
from django_cassandra_engine.models import DjangoCassandraModel
from django_cassandra_engine.utils import get_engine_from_db_alias
from cassandra.cqlengine import management
from cassandra.cqlengine.models import Model as CqlModel

from features.course.classroom.models.classroom import Classroom
from features.course.classroom.models.classroom_member import ClassroomMember
from features.resource.models.resource_folder import ResourceFolder


def sync_model(model, alias):
    name = model.__table_name__
    try:
        # Patch the tuple used for type check inside sync_table
        management.Model = (CqlModel, DjangoCassandraModel)
        management.sync_table(model, keyspaces=[connections[alias].settings_dict['NAME']], connections=[alias])
        print(f"[sync_adhoc] OK   {name}")
    except Exception as exc:
        print(f"[sync_adhoc] FAIL {name}: {exc}")


if __name__ == '__main__':
    for alias in connections:
        if get_engine_from_db_alias(alias) != 'django_cassandra_engine':
            continue
        for m in (Classroom, ResourceFolder, ClassroomMember):
            sync_model(m, alias)
