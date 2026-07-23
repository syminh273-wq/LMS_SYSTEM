"""
Sync Cassandra tables — tạo các table còn thiếu trong Cassandra mà không cần drop.
Usage: python manage.py lms_sync_cassandra
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from cassandra.cqlengine import management
from cassandra.cqlengine.models import Model as CqlModel
from cassandra.cqlengine.management import drop_table, sync_table, create_keyspace_simple
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from django_cassandra_engine.models import DjangoCassandraModel

from features.social.models import (
    ConsumerPost, PostLike, PostComment, UserFollow,
    UserProfile, ClassroomFavorite,
)
from features.chat.models import Conversation, ConversationMember, Message


def _cassandra_cfg():
    return settings.DATABASES.get('default', {})


def _make_cluster(hosts, cfg):
    """Build a Cluster with auth_provider when credentials are configured."""
    kwargs = {
        'contact_points': hosts if isinstance(hosts, list) else [hosts],
    }
    user = (cfg.get('USER') or cfg.get('USERNAME') or '').strip()
    pwd = cfg.get('PASSWORD') or ''
    if user:
        kwargs['auth_provider'] = PlainTextAuthProvider(username=user, password=pwd)
    return Cluster(**kwargs)


def _is_auth_error(exc) -> bool:
    msg = str(exc).lower()
    return (
        'authenticationfailed' in msg
        or 'unable to connect' in msg
        or 'requires authentication' in msg
    )


def _add_missing_columns(model, keyspace, hosts, cfg, stdout):
    """ALTER TABLE to add columns that exist on the model but not in the schema."""
    try:
        cluster = _make_cluster(hosts, cfg)
        session = cluster.connect(keyspace)
        rows = session.execute(
            "SELECT column_name FROM system_schema.columns "
            "WHERE keyspace_name=%s AND table_name=%s",
            (keyspace, model.__table_name__)
        )
        existing = {r.column_name for r in rows}
        cluster.shutdown()
    except Exception as e:
        if _is_auth_error(e):
            stdout.write(f'  AUTH FAIL: cannot connect to Cassandra — {e}')
        else:
            stdout.write(f'  could not read schema for {model.__table_name__}: {e}')
        return

    type_map = {
        'UUID':        'uuid',
        'Text':        'text',
        'Integer':     'int',
        'DateTime':    'timestamp',
        'Boolean':     'boolean',
        'Float':       'float',
        'Double':      'double',
        'BigInt':      'bigint',
        'TimeUUID':    'timeuuid',
    }

    from cassandra.cqlengine import columns as c_cols
    for name, col in model._columns.items():
        if name in existing:
            continue
        if getattr(col, 'primary_key', False) or getattr(col, 'partition_key', False):
            continue
        cql_type = type_map.get(type(col).__name__)
        if cql_type is None:
            continue
        if isinstance(col, c_cols.List):
            inner = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'list<{inner}>'
        elif isinstance(col, c_cols.Set):
            inner = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'set<{inner}>'
        elif isinstance(col, c_cols.Map):
            k = type_map.get(type(col.key_type).__name__, 'text')
            v = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'map<{k},{v}>'

        try:
            cluster = _make_cluster(hosts, cfg)
            session = cluster.connect(keyspace)
            session.execute(
                f'ALTER TABLE {model.__table_name__} ADD {name} {cql_type}'
            )
            cluster.shutdown()
            stdout.write(f'  + added column {name} {cql_type} to {model.__table_name__}')
        except Exception as e:
            stdout.write(f'  ! failed to add {name} to {model.__table_name__}: {e}')


class Command(BaseCommand):
    help = 'Sync all Cassandra tables (create if not exists)'

    def handle(self, *args, **options):
        cfg = _cassandra_cfg()
        keyspace = cfg.get('NAME')
        hosts = cfg.get('HOST', '127.0.0.1')

        # Allow sync_table() to accept DjangoCassandraModel subclasses.
        # cqlengine's _sync_table does `issubclass(model, Model)`; without this
        # patch every model raises "Models must be derived from base Model."
        management.Model = (CqlModel, DjangoCassandraModel)

        # Ensure keyspace exists
        try:
            if keyspace and hosts:
                create_keyspace_simple(keyspace, replication_factor=1)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'keyspace check: {e}'))

        models = [
            ('social.UserProfile',     UserProfile),
            ('social.ConsumerPost',    ConsumerPost),
            ('social.PostLike',        PostLike),
            ('social.PostComment',     PostComment),
            ('social.UserFollow',      UserFollow),
            ('social.ClassroomFavorite', ClassroomFavorite),
            ('chat.Conversation',      Conversation),
            ('chat.ConversationMember', ConversationMember),
            ('chat.Message',           Message),
        ]

        for label, model in models:
            try:
                sync_table(model)
                self.stdout.write(self.style.SUCCESS(f'OK   {label}'))
            except Exception as e:
                msg = str(e)
                if 'already exists' in msg.lower() or 'unconfigured table' in msg.lower():
                    self.stdout.write(f'SKIP {label} ({msg[:60]})')
                elif _is_auth_error(e):
                    self.stdout.write(self.style.ERROR(f'AUTH FAIL {label}: {e}'))
                else:
                    self.stdout.write(self.style.ERROR(f'FAIL {label}: {e}'))

            try:
                _add_missing_columns(model, keyspace, hosts, cfg, self.stdout)
            except Exception as e:
                self.stdout.write(f'  column check failed for {label}: {e}')

        self.stdout.write(self.style.SUCCESS('Sync done.'))


