from cassandra import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import AddressTranslator, FallthroughRetryPolicy
from decouple import config

DB_HOST = config('DB_HOST', default='127.0.0.1')
DB_PORT = config('DB_PORT', cast=int, default=9042)


class ContactPointTranslator(AddressTranslator):
    """Map every discovered cluster IP back to the configured contact point.

    When ScyllaDB/Cassandra runs in Docker it advertises its internal network
    IP (e.g. 192.168.97.2) through gossip.  The driver then tries to open
    connection pools to that internal IP, which is unreachable from the host.
    This translator intercepts the address lookup and returns the host we
    actually want to talk to instead.
    """

    def __init__(self, contact_point: str):
        self._contact_point = contact_point

    def translate(self, addr: str) -> str:
        return self._contact_point


DATABASES = {
    'default': {
        'ENGINE': 'django_cassandra_engine',
        'NAME': config('DB_DATABASE'),
        'HOST': DB_HOST,
        'PORT': str(DB_PORT),
        'USER': config('DB_USERNAME'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'OPTIONS': {
            'replication': {
                'strategy_class': 'SimpleStrategy',
                'replication_factor': 1,
            },
            'connection': {
                'consistency': ConsistencyLevel.LOCAL_QUORUM,
                'retry_connect': True,
                'port': DB_PORT,
                'default_retry_policy': FallthroughRetryPolicy(),
                'address_translator': ContactPointTranslator(DB_HOST),
                'auth_provider': PlainTextAuthProvider(
                    config('DB_USERNAME'),
                    config('DB_PASSWORD')
                ),
            },
            'session': {
                'default_timeout': 10,
                'default_fetch_size': 10000,
            },
        }
    },
}

PRIMARY_DB = config('PRIMARY_DB', 'default')
SESSION_ENGINE = 'django_cassandra_engine.sessions.backends.db'
CASSANDRA_FALLBACK_ORDER_BY_PYTHON = False
