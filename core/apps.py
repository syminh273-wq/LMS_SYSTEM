from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        _patch_cqlengine_index_lookup()
        _typesense_auto_init()


def _patch_cqlengine_index_lookup():
    """
    Fix cassandra-driver bug: _get_index_name_by_column only checks index_options['target'],
    which is absent on indexes created by older driver versions or ScyllaDB.
    When 'target' is missing the driver thinks the index doesn't exist and tries to create a
    duplicate (e.g. _token_idx_1), which Cassandra rejects with InvalidRequest.

    This patch adds a fallback that matches indexes by their auto-generated name pattern:
    {table}_{column}_idx[_N]
    """
    from cassandra.cqlengine import management as mgmt

    _original = mgmt._get_index_name_by_column

    def _patched(table, column_name):
        result = _original(table, column_name)
        if result:
            return result

        # Fallback: match by Cassandra's auto-generated name pattern
        prefix = "{}_{}".format(table.name, column_name)
        for index_name in table.indexes:
            if index_name == prefix + "_idx" or index_name.startswith(prefix + "_idx_"):
                return index_name

        return None

    mgmt._get_index_name_by_column = _patched


def _typesense_auto_init():
    """Auto-create / patch Typesense collections on startup. Never blocks boot."""
    import sys
    # Skip during migrate, shell, test — only run for the real server/worker
    skip_commands = {'migrate', 'makemigrations', 'shell', 'test', 'collectstatic'}
    if any(cmd in sys.argv for cmd in skip_commands):
        return
    try:
        from core.search_engine.typesense.service import TypesenseService
        TypesenseService().initialize_collections()
    except Exception:
        pass
