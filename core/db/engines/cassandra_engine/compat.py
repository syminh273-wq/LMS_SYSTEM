"""Handle package compatibility."""

try:
    from cassandra import cqlengine
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.cluster import Cluster, Session
    from cassandra.cqlengine import (
        CQLEngineException,
        columns,
        connection,
        query,
    )
    from cassandra.cqlengine.management import (
        create_keyspace_simple,
        create_keyspace_network_topology,
        drop_keyspace,
        sync_table,
    )
    from cassandra.cqlengine import management
    from cassandra.cqlengine.models import (
        BaseModel,
        ColumnDescriptor,
        Model,
        ModelDefinitionException,
        ModelException,
        ModelMetaClass,
    )
    from cassandra.util import OrderedDict

except ImportError:
    raise ImportError("You must install cassandra-driver!")
